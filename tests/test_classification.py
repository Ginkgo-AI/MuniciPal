"""Tests for the data classification rules engine."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from municipal.classification.rules import ClassificationEngine
from municipal.core.types import DataClassification


@pytest.fixture()
def config_path(tmp_path: Path) -> Path:
    """Write a minimal classification config and return its path."""
    config = {
        "rules": [
            {
                "name": "legal_correspondence",
                "description": "Legal communications",
                "resource_types": ["legal_correspondence", "legal_memo"],
                "classification": "restricted",
            },
            {
                "name": "resident_pii",
                "description": "Resident PII",
                "resource_types": ["resident_pii", "contact_info"],
                "classification": "sensitive",
            },
            {
                "name": "staff_sops",
                "description": "Staff SOPs",
                "resource_types": ["staff_sop", "internal_procedure"],
                "classification": "internal",
            },
            {
                "name": "published_ordinances",
                "description": "Published ordinances",
                "resource_types": ["ordinance", "resolution"],
                "classification": "public",
            },
        ],
        "default_classification": "sensitive",
        "context_overrides": [
            {"condition": "uncertain", "escalate_to": "sensitive"},
            {"condition": "external_source", "minimum": "internal"},
        ],
    }
    path = tmp_path / "classification.yml"
    path.write_text(yaml.dump(config))
    return path


@pytest.fixture()
def engine(config_path: Path) -> ClassificationEngine:
    """Create a ClassificationEngine from the test config."""
    return ClassificationEngine(config_path=config_path)


class TestClassificationEngine:
    """Tests for ClassificationEngine."""

    def test_classify_resident_pii_as_sensitive(self, engine: ClassificationEngine) -> None:
        result = engine.classify("resident_pii")
        assert result == DataClassification.SENSITIVE

    def test_classify_ordinance_as_public(self, engine: ClassificationEngine) -> None:
        result = engine.classify("ordinance")
        assert result == DataClassification.PUBLIC

    def test_classify_legal_correspondence_as_restricted(self, engine: ClassificationEngine) -> None:
        result = engine.classify("legal_correspondence")
        assert result == DataClassification.RESTRICTED

    def test_classify_staff_sop_as_internal(self, engine: ClassificationEngine) -> None:
        result = engine.classify("staff_sop")
        assert result == DataClassification.INTERNAL

    def test_unknown_resource_uses_default(self, engine: ClassificationEngine) -> None:
        result = engine.classify("unknown_resource_type")
        assert result == DataClassification.SENSITIVE

    def test_context_uncertain_escalates(self, engine: ClassificationEngine) -> None:
        # Public resource escalated to Sensitive when uncertain
        result = engine.classify("ordinance", context={"uncertain": True})
        assert result == DataClassification.SENSITIVE

    def test_context_uncertain_does_not_downgrade(self, engine: ClassificationEngine) -> None:
        # Restricted should stay Restricted even with uncertain context
        result = engine.classify("legal_correspondence", context={"uncertain": True})
        assert result == DataClassification.RESTRICTED

    def test_context_external_source_minimum(self, engine: ClassificationEngine) -> None:
        # Public resource from external source should be at least Internal
        result = engine.classify("ordinance", context={"external_source": True})
        assert result == DataClassification.INTERNAL

    def test_first_match_wins(self, engine: ClassificationEngine) -> None:
        # contact_info matches resident_pii rule
        result = engine.classify("contact_info")
        assert result == DataClassification.SENSITIVE

    def test_get_rule_returns_matching_rule(self, engine: ClassificationEngine) -> None:
        rule = engine.get_rule("staff_sop")
        assert rule is not None
        assert rule.name == "staff_sops"
        assert rule.classification == DataClassification.INTERNAL

    def test_get_rule_returns_none_for_unknown(self, engine: ClassificationEngine) -> None:
        rule = engine.get_rule("nonexistent")
        assert rule is None

    def test_rules_property(self, engine: ClassificationEngine) -> None:
        rules = engine.rules
        assert len(rules) == 4

    def test_default_classification_property(self, engine: ClassificationEngine) -> None:
        assert engine.default_classification == DataClassification.SENSITIVE


class TestProductionConfig:
    """Test that the production YAML config loads correctly."""

    def test_production_config_loads(self) -> None:
        """Verify the actual config/data_classification.yml is valid."""
        config_path = (
            Path(__file__).resolve().parents[1] / "config" / "data_classification.yml"
        )
        if not config_path.exists():
            pytest.skip("Production config not found")

        engine = ClassificationEngine(config_path=config_path)
        assert len(engine.rules) > 0

        # Spot-check a few known classifications
        assert engine.classify("resident_pii") == DataClassification.SENSITIVE
        assert engine.classify("ordinance") == DataClassification.PUBLIC
        assert engine.classify("legal_correspondence") == DataClassification.RESTRICTED
        assert engine.classify("staff_sop") == DataClassification.INTERNAL
