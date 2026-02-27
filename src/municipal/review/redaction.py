"""Rule-based PII/sensitive data detection for FOIA redaction suggestions."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from municipal.core.types import DataClassification
from municipal.review.models import Confidence, RedactionReport, RedactionSuggestion

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "redaction_rules.yml"

# Classification sensitivity ordering
_CLASSIFICATION_ORDER = {
    DataClassification.PUBLIC: 0,
    DataClassification.INTERNAL: 1,
    DataClassification.SENSITIVE: 2,
    DataClassification.RESTRICTED: 3,
}


class RedactionEngine:
    """Scans case data and suggests redactions based on PII patterns and field classification.

    Staff reviews and decides — no automatic redaction.
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config_path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._pattern_rules: list[dict[str, Any]] = []
        self._compiled_patterns: dict[str, re.Pattern] = {}
        self._field_rules: list[dict[str, Any]] = []
        self._compiled_field_patterns: dict[str, re.Pattern] = {}
        self._classification_threshold: str = "sensitive"
        self._load_config()

    def _compile_pattern(self, pattern: str, label: str) -> re.Pattern | None:
        """Compile a regex pattern with validation. Returns None if invalid."""
        try:
            return re.compile(pattern)
        except re.error as exc:
            logger.warning("Invalid regex pattern in %s: %r — %s", label, pattern, exc)
            return None

    def _load_config(self) -> None:
        if not self._config_path.exists():
            return
        with open(self._config_path) as fh:
            data = yaml.safe_load(fh) or {}

        self._pattern_rules = data.get("pattern_rules", [])
        self._field_rules = data.get("field_rules", [])
        self._classification_threshold = data.get("classification_threshold", "sensitive")

        # Pre-compile all regex patterns at load time
        for rule in self._pattern_rules:
            pattern = rule.get("pattern", "")
            if pattern:
                compiled = self._compile_pattern(pattern, "pattern_rules")
                if compiled:
                    self._compiled_patterns[pattern] = compiled

        for rule in self._field_rules:
            pattern = rule.get("field_pattern", "")
            if pattern:
                compiled = self._compile_pattern(pattern, "field_rules")
                if compiled:
                    self._compiled_field_patterns[pattern] = compiled

    def scan(
        self,
        case_id: str,
        data: dict[str, Any],
        field_classifications: dict[str, str] | None = None,
    ) -> RedactionReport:
        """Scan case data and return redaction suggestions.

        Args:
            case_id: The case identifier.
            data: Merged case data (field_id -> value).
            field_classifications: Optional map of field_id -> DataClassification value.

        Returns:
            RedactionReport with suggestions.
        """
        suggestions: list[RedactionSuggestion] = []
        field_classifications = field_classifications or {}

        for field_id, value in data.items():
            if value is None:
                continue
            str_value = str(value)
            if not str_value.strip():
                continue

            # Check pattern-based rules
            for rule in self._pattern_rules:
                pattern = rule.get("pattern", "")
                if not pattern:
                    continue
                compiled = self._compiled_patterns.get(pattern)
                if compiled is None:
                    continue
                if compiled.search(str_value):
                    snippet = self._make_snippet(str_value)
                    suggestions.append(RedactionSuggestion(
                        field_id=field_id,
                        value_snippet=snippet,
                        reason=rule.get("reason", "Matches PII pattern"),
                        confidence=Confidence(rule.get("confidence", "medium")),
                        classification=rule.get("classification", "sensitive"),
                    ))

            # Check field classification threshold
            field_class = field_classifications.get(field_id)
            if field_class:
                threshold_level = _CLASSIFICATION_ORDER.get(
                    DataClassification(self._classification_threshold), 2
                )
                field_level = _CLASSIFICATION_ORDER.get(
                    DataClassification(field_class), 0
                )
                if field_level >= threshold_level:
                    # Don't duplicate if already flagged by pattern
                    already_flagged = any(
                        s.field_id == field_id for s in suggestions
                    )
                    if not already_flagged:
                        snippet = self._make_snippet(str_value)
                        suggestions.append(RedactionSuggestion(
                            field_id=field_id,
                            value_snippet=snippet,
                            reason=f"Field classified as {field_class}",
                            confidence=Confidence.MEDIUM,
                            classification=field_class,
                        ))

            # Check field-name-based rules
            for rule in self._field_rules:
                field_pattern = rule.get("field_pattern", "")
                compiled_fp = self._compiled_field_patterns.get(field_pattern)
                if compiled_fp and compiled_fp.search(field_id):
                    already_flagged = any(
                        s.field_id == field_id for s in suggestions
                    )
                    if not already_flagged:
                        snippet = self._make_snippet(str_value)
                        suggestions.append(RedactionSuggestion(
                            field_id=field_id,
                            value_snippet=snippet,
                            reason=rule.get("reason", "Field name matches sensitive pattern"),
                            confidence=Confidence(rule.get("confidence", "medium")),
                            classification=rule.get("classification", "sensitive"),
                        ))

        return RedactionReport(case_id=case_id, suggestions=suggestions)

    @staticmethod
    def _make_snippet(value: str, max_len: int = 50) -> str:
        if len(value) <= max_len:
            return value
        return value[:max_len] + "..."
