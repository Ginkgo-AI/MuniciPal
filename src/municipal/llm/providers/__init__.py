"""Provider registry for LLM backends."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from municipal.llm.client import LLMClient

from municipal.llm.providers.ollama import OllamaClient
from municipal.llm.providers.openai_compat import OpenAICompatClient

PROVIDER_REGISTRY: dict[str, type[LLMClient]] = {
    "ollama": OllamaClient,
    "openai": OpenAICompatClient,
    "vllm": OpenAICompatClient,
}

__all__ = ["PROVIDER_REGISTRY", "OllamaClient", "OpenAICompatClient"]
