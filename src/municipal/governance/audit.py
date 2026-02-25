"""Immutable audit logger for Munici-Pal.

Writes append-only, hash-chained log entries to JSONL files.
Each entry's SHA-256 hash includes the previous entry's hash, forming a
tamper-evident chain. Altering any entry breaks the chain for all
subsequent entries.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from municipal.core.config import AuditConfig
from municipal.core.types import AuditEvent


class AuditEntry:
    """Wrapper around an AuditEvent with chain hash metadata."""

    def __init__(self, event: AuditEvent, previous_hash: str, entry_hash: str) -> None:
        self.event = event
        self.previous_hash = previous_hash
        self.entry_hash = entry_hash

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict suitable for JSONL output."""
        return {
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
            "event": json.loads(self.event.model_dump_json()),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEntry:
        """Deserialize from a JSONL dict."""
        event = AuditEvent(**data["event"])
        return cls(
            event=event,
            previous_hash=data["previous_hash"],
            entry_hash=data["entry_hash"],
        )


class AuditLogger:
    """Append-only, hash-chained audit logger.

    Each log entry's hash = SHA-256(previous_hash + entry_json), creating a
    tamper-evident chain. Entries are written to JSONL files (one line per entry).

    Args:
        config: AuditConfig instance. Defaults to AuditConfig() which reads
            from environment variables.
        log_file: Override the log file name (default: ``audit.jsonl``).
    """

    def __init__(
        self,
        config: AuditConfig | None = None,
        log_file: str = "audit.jsonl",
    ) -> None:
        self._config = config or AuditConfig()
        self._log_dir = Path(self._config.log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._log_dir / log_file
        self._last_hash: str = self._compute_genesis_hash()

        # If the log file already exists, recover the last hash from the chain
        if self._log_path.exists():
            self._recover_last_hash()

    @staticmethod
    def _compute_genesis_hash() -> str:
        """Return the genesis (seed) hash for the first entry in a chain."""
        return hashlib.sha256(b"municipal-genesis").hexdigest()

    def _recover_last_hash(self) -> None:
        """Read the existing log file and recover the last entry's hash."""
        last_line: str | None = None
        with open(self._log_path) as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    last_line = stripped

        if last_line:
            data = json.loads(last_line)
            self._last_hash = data["entry_hash"]

    def _compute_hash(self, previous_hash: str, entry_json: str) -> str:
        """Compute SHA-256(previous_hash + entry_json)."""
        payload = (previous_hash + entry_json).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def log(self, event: AuditEvent) -> AuditEntry:
        """Append an audit event to the log.

        The event is serialized to JSON, hashed with the previous entry's
        hash, and written as a single JSONL line.

        Args:
            event: The AuditEvent to log.

        Returns:
            The AuditEntry with computed hash metadata.
        """
        event_json = event.model_dump_json()
        entry_hash = self._compute_hash(self._last_hash, event_json)

        entry = AuditEntry(
            event=event,
            previous_hash=self._last_hash,
            entry_hash=entry_hash,
        )

        # Append to JSONL file
        with open(self._log_path, "a") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")

        self._last_hash = entry_hash
        return entry

    def verify_chain(self) -> bool:
        """Verify the integrity of the entire hash chain.

        Reads all entries from the log file and recomputes each hash.
        Returns True if the chain is intact, False if any entry has been
        tampered with.
        """
        if not self._log_path.exists():
            return True  # Empty chain is trivially valid

        previous_hash = self._compute_genesis_hash()

        with open(self._log_path) as fh:
            for line_number, line in enumerate(fh, start=1):
                stripped = line.strip()
                if not stripped:
                    continue

                data = json.loads(stripped)
                stored_previous = data["previous_hash"]
                stored_hash = data["entry_hash"]

                # Verify previous hash linkage
                if stored_previous != previous_hash:
                    return False

                # Recompute hash from the event data
                event = AuditEvent(**data["event"])
                event_json = event.model_dump_json()
                expected_hash = self._compute_hash(previous_hash, event_json)

                if stored_hash != expected_hash:
                    return False

                previous_hash = stored_hash

        return True

    def query(self, filters: dict[str, Any] | None = None) -> list[AuditEvent]:
        """Query audit events with optional filters.

        Supported filter keys:
            - ``actor``: exact match on actor field
            - ``action``: exact match on action field
            - ``resource``: exact match on resource field
            - ``classification``: exact match on classification field
            - ``session_id``: exact match on session_id field
            - ``after``: ISO datetime string; only events after this time
            - ``before``: ISO datetime string; only events before this time

        Args:
            filters: Optional dict of filter criteria.

        Returns:
            List of matching AuditEvent instances.
        """
        filters = filters or {}
        results: list[AuditEvent] = []

        if not self._log_path.exists():
            return results

        after_dt = None
        before_dt = None
        if "after" in filters:
            after_dt = datetime.fromisoformat(filters["after"])
            if after_dt.tzinfo is None:
                after_dt = after_dt.replace(tzinfo=timezone.utc)
        if "before" in filters:
            before_dt = datetime.fromisoformat(filters["before"])
            if before_dt.tzinfo is None:
                before_dt = before_dt.replace(tzinfo=timezone.utc)

        with open(self._log_path) as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue

                data = json.loads(stripped)
                event = AuditEvent(**data["event"])

                # Apply filters
                if "actor" in filters and event.actor != filters["actor"]:
                    continue
                if "action" in filters and event.action != filters["action"]:
                    continue
                if "resource" in filters and event.resource != filters["resource"]:
                    continue
                if "classification" in filters and event.classification != filters["classification"]:
                    continue
                if "session_id" in filters and event.session_id != filters["session_id"]:
                    continue
                if after_dt and event.timestamp <= after_dt:
                    continue
                if before_dt and event.timestamp >= before_dt:
                    continue

                results.append(event)

        return results

    @property
    def log_path(self) -> Path:
        """Path to the current JSONL log file."""
        return self._log_path

    @property
    def last_hash(self) -> str:
        """The hash of the most recent entry (or genesis hash if empty)."""
        return self._last_hash
