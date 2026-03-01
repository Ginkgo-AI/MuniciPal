"""Abstract LLM client interface and factory function."""

from __future__ import annotations

import abc
from typing import AsyncIterator

from municipal.core.config import LLMConfig


class LLMClient(abc.ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @abc.abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        """Generate a completion from a single prompt."""

    @abc.abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.1,
    ) -> AsyncIterator[str]:
        """Stream tokens from a completion. Yields text chunks."""
        yield ""  # pragma: no cover

    @abc.abstractmethod
    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.1,
    ) -> str:
        """Generate a response from a list of chat messages."""

    @abc.abstractmethod
    async def is_available(self) -> bool:
        """Return True if the provider is reachable."""

    async def close(self) -> None:
        """Clean up resources. Override if the provider holds connections."""


def create_llm_client(config: LLMConfig) -> LLMClient:
    """Factory: select and instantiate an LLM provider based on config.provider."""

    from municipal.llm.providers import PROVIDER_REGISTRY

    provider = config.provider.lower()
    if provider not in PROVIDER_REGISTRY:
        available = ", ".join(sorted(PROVIDER_REGISTRY))
        raise ValueError(
            f"Unknown LLM provider {config.provider!r}. "
            f"Available: {available}"
        )

    cls = PROVIDER_REGISTRY[provider]
    return cls(config)
