"""Model registry for production/candidate model tracking and promotion."""

from __future__ import annotations

from municipal.core.config import LLMConfig


class ModelRegistry:
    """Tracks production and candidate LLM configurations.

    Supports promoting the candidate model to production.
    """

    def __init__(self, production: LLMConfig | None = None) -> None:
        self._production = production
        self._candidate: LLMConfig | None = None

    def set_production(self, config: LLMConfig) -> None:
        self._production = config

    def set_candidate(self, config: LLMConfig) -> None:
        self._candidate = config

    def get_production(self) -> LLMConfig | None:
        return self._production

    def get_candidate(self) -> LLMConfig | None:
        return self._candidate

    def promote_candidate(self) -> LLMConfig:
        """Promote the candidate to production.

        Returns the newly promoted config.

        Raises:
            ValueError: If no candidate is set.
        """
        if self._candidate is None:
            raise ValueError("No candidate model to promote")
        self._production = self._candidate
        self._candidate = None
        return self._production

    def has_candidate(self) -> bool:
        return self._candidate is not None

    def summary(self) -> dict[str, dict | None]:
        return {
            "production": self._production.model_dump(exclude={"api_key"}) if self._production else None,
            "candidate": self._candidate.model_dump(exclude={"api_key"}) if self._candidate else None,
        }
