"""Classification rules engine for Munici-Pal.

Loads classification rules from YAML config and determines the appropriate
DataClassification level for a given resource type and context.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from municipal.core.types import DataClassification

# Default path to the classification rules config
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "data_classification.yml"

# Classification level ordering for comparison (higher = more restrictive)
_LEVEL_ORDER: dict[DataClassification, int] = {
    DataClassification.PUBLIC: 1,
    DataClassification.INTERNAL: 2,
    DataClassification.SENSITIVE: 3,
    DataClassification.RESTRICTED: 4,
}


class ClassificationRule:
    """A single classification rule loaded from config."""

    def __init__(
        self,
        name: str,
        description: str,
        resource_types: list[str],
        classification: str,
        residency: str = "any",
        cache: str = "allowed",
        logging: str = "standard",
    ) -> None:
        self.name = name
        self.description = description
        self.resource_types = resource_types
        self.classification = DataClassification(classification)
        self.residency = residency
        self.cache = cache
        self.logging = logging

    def matches(self, resource_type: str) -> bool:
        """Check whether this rule matches the given resource type."""
        return resource_type in self.resource_types


class ClassificationEngine:
    """Rule-based classification engine.

    Loads rules from a YAML config file and evaluates them in order.
    First matching rule wins. Falls back to the configured default
    classification (Sensitive) when no rule matches.
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config_path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._rules: list[ClassificationRule] = []
        self._default: DataClassification = DataClassification.SENSITIVE
        self._context_overrides: list[dict[str, str]] = []
        self._load_config()

    def _load_config(self) -> None:
        """Load and parse the YAML configuration file."""
        with open(self._config_path) as fh:
            config = yaml.safe_load(fh)

        for rule_data in config.get("rules", []):
            self._rules.append(
                ClassificationRule(
                    name=rule_data["name"],
                    description=rule_data.get("description", ""),
                    resource_types=rule_data.get("resource_types", []),
                    classification=rule_data["classification"],
                    residency=rule_data.get("residency", "any"),
                    cache=rule_data.get("cache", "allowed"),
                    logging=rule_data.get("logging", "standard"),
                )
            )

        default_raw = config.get("default_classification", "sensitive")
        self._default = DataClassification(default_raw)
        self._context_overrides = config.get("context_overrides", [])

    def classify(self, resource_type: str, context: dict[str, Any] | None = None) -> DataClassification:
        """Determine classification level for a resource type and context.

        Args:
            resource_type: The type identifier of the resource being classified.
            context: Optional dict with contextual hints (e.g. ``uncertain``,
                ``external_source``).

        Returns:
            The appropriate DataClassification level.
        """
        context = context or {}
        classification = self._default

        # Evaluate rules in order; first match wins
        for rule in self._rules:
            if rule.matches(resource_type):
                classification = rule.classification
                break

        # Apply context-based overrides
        classification = self._apply_context_overrides(classification, context)

        return classification

    def _apply_context_overrides(
        self,
        classification: DataClassification,
        context: dict[str, Any],
    ) -> DataClassification:
        """Apply context-based overrides to the classification."""
        for override in self._context_overrides:
            condition = override.get("condition", "")

            if condition == "uncertain" and context.get("uncertain", False):
                target = DataClassification(override.get("escalate_to", "sensitive"))
                if _LEVEL_ORDER.get(target, 0) > _LEVEL_ORDER.get(classification, 0):
                    classification = target

            if condition == "external_source" and context.get("external_source", False):
                minimum = DataClassification(override.get("minimum", "internal"))
                if _LEVEL_ORDER.get(minimum, 0) > _LEVEL_ORDER.get(classification, 0):
                    classification = minimum

        return classification

    def get_rule(self, resource_type: str) -> ClassificationRule | None:
        """Return the first matching rule for a resource type, or None."""
        for rule in self._rules:
            if rule.matches(resource_type):
                return rule
        return None

    @property
    def rules(self) -> list[ClassificationRule]:
        """All loaded classification rules."""
        return list(self._rules)

    @property
    def default_classification(self) -> DataClassification:
        """The default classification when no rule matches."""
        return self._default


# Module-level convenience: singleton engine and classify function
_engine: ClassificationEngine | None = None


def _get_engine() -> ClassificationEngine:
    global _engine
    if _engine is None:
        _engine = ClassificationEngine()
    return _engine


def classify(resource_type: str, context: dict[str, Any] | None = None) -> DataClassification:
    """Convenience function to classify a resource type.

    Uses a module-level singleton ``ClassificationEngine`` with the default
    config path.
    """
    return _get_engine().classify(resource_type, context)
