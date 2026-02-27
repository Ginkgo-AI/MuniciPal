"""PostgreSQL audit repository preserving hash chain integrity."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from municipal.core.config import AuditConfig
from municipal.core.types import AuditEvent, DataClassification
from municipal.db.engine import DatabaseManager
from municipal.db.models import AuditEventRow
from municipal.governance.audit import AuditEntry


class PostgresAuditRepository:
    """Postgres-backed audit logger preserving tamper-evident hash chain."""

    def __init__(self, db: DatabaseManager, config: AuditConfig | None = None) -> None:
        self._db = db
        self._config = config or AuditConfig()
        self._last_hash: str = self._compute_genesis_hash()
        self._lock = asyncio.Lock()

    @staticmethod
    def _compute_genesis_hash() -> str:
        return hashlib.sha256(b"municipal-genesis").hexdigest()

    def _compute_hash(self, previous_hash: str, entry_json: str) -> str:
        payload = (previous_hash + entry_json).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    async def _recover_last_hash(self) -> None:
        async with self._db.session() as db:
            result = await db.execute(
                select(AuditEventRow).order_by(AuditEventRow.timestamp.desc()).limit(1)
            )
            row = result.scalar_one_or_none()
            if row and row.entry_hash:
                self._last_hash = row.entry_hash

    async def log(self, event: AuditEvent) -> AuditEntry:
        async with self._lock:
            await self._recover_last_hash()
            event_json = event.model_dump_json()
            entry_hash = self._compute_hash(self._last_hash, event_json)

            entry = AuditEntry(
                event=event,
                previous_hash=self._last_hash,
                entry_hash=entry_hash,
            )

            async with self._db.session() as db:
                event_data = json.loads(event_json)
                row = AuditEventRow(
                    event_id=event.event_id,
                    timestamp=event.timestamp,
                    session_id=event.session_id,
                    actor=event.actor,
                    action=event.action,
                    resource=event.resource,
                    classification=event.classification.value,
                    details=event_data.get("details", {}),
                    prompt_version=event.prompt_version,
                    tool_calls=event_data.get("tool_calls", []),
                    data_sources=event_data.get("data_sources", []),
                    approval_chain=event_data.get("approval_chain", []),
                    previous_hash=self._last_hash,
                    entry_hash=entry_hash,
                )
                db.add(row)
                await db.commit()

            self._last_hash = entry_hash
            return entry

    async def verify_chain(self) -> bool:
        """Verify hash chain linkage.

        Each row's previous_hash must equal the preceding row's entry_hash,
        and the first row's previous_hash must equal the genesis hash.
        """
        async with self._db.session() as db:
            result = await db.execute(
                select(AuditEventRow).order_by(AuditEventRow.timestamp)
            )
            rows = result.scalars().all()

        if not rows:
            return True

        expected_previous = self._compute_genesis_hash()
        for row in rows:
            if row.previous_hash != expected_previous:
                return False
            if not row.entry_hash:
                return False
            expected_previous = row.entry_hash

        return True

    async def query(self, filters: dict[str, Any] | None = None) -> list[AuditEvent]:
        filters = filters or {}
        async with self._db.session() as db:
            stmt = select(AuditEventRow)

            if "actor" in filters:
                stmt = stmt.where(AuditEventRow.actor == filters["actor"])
            if "action" in filters:
                stmt = stmt.where(AuditEventRow.action == filters["action"])
            if "resource" in filters:
                stmt = stmt.where(AuditEventRow.resource == filters["resource"])
            if "classification" in filters:
                stmt = stmt.where(AuditEventRow.classification == filters["classification"])
            if "session_id" in filters:
                stmt = stmt.where(AuditEventRow.session_id == filters["session_id"])
            if "after" in filters:
                after_dt = datetime.fromisoformat(filters["after"])
                if after_dt.tzinfo is None:
                    after_dt = after_dt.replace(tzinfo=timezone.utc)
                stmt = stmt.where(AuditEventRow.timestamp > after_dt)
            if "before" in filters:
                before_dt = datetime.fromisoformat(filters["before"])
                if before_dt.tzinfo is None:
                    before_dt = before_dt.replace(tzinfo=timezone.utc)
                stmt = stmt.where(AuditEventRow.timestamp < before_dt)

            result = await db.execute(stmt)
            return [
                AuditEvent(
                    event_id=r.event_id,
                    timestamp=r.timestamp,
                    session_id=r.session_id,
                    actor=r.actor,
                    action=r.action,
                    resource=r.resource,
                    classification=DataClassification(r.classification),
                    details=r.details or {},
                    prompt_version=r.prompt_version,
                    tool_calls=r.tool_calls or [],
                    data_sources=r.data_sources or [],
                    approval_chain=r.approval_chain or [],
                )
                for r in result.scalars().all()
            ]

    @property
    def log_path(self) -> None:
        return None

    @property
    def last_hash(self) -> str:
        return self._last_hash
