"""Unit tests for the LLM client abstraction layer."""

from __future__ import annotations

import pytest
import httpx

from municipal.core.config import LLMConfig
from municipal.core.types import HealthStatus
from municipal.llm.client import LLMClient, create_llm_client
from municipal.llm.providers.ollama import OllamaClient
from municipal.llm.providers.openai_compat import OpenAICompatClient
from municipal.llm.health import check_llm_health


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ollama_config(**overrides) -> LLMConfig:
    defaults = {"provider": "ollama", "base_url": "http://localhost:11434", "model": "llama3.1:8b"}
    defaults.update(overrides)
    return LLMConfig(**defaults)


def _openai_config(**overrides) -> LLMConfig:
    defaults = {"provider": "openai", "base_url": "http://localhost:8000", "model": "mistral"}
    defaults.update(overrides)
    return LLMConfig(**defaults)


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------

class TestFactory:
    def test_creates_ollama_client(self):
        client = create_llm_client(_ollama_config())
        assert isinstance(client, OllamaClient)

    def test_creates_openai_client(self):
        client = create_llm_client(_openai_config())
        assert isinstance(client, OpenAICompatClient)

    def test_creates_vllm_client(self):
        client = create_llm_client(_openai_config(provider="vllm"))
        assert isinstance(client, OpenAICompatClient)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm_client(_ollama_config(provider="nope"))


# ---------------------------------------------------------------------------
# Ollama provider tests
# ---------------------------------------------------------------------------

class TestOllamaClient:
    @pytest.mark.asyncio
    async def test_generate(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:11434/api/generate",
            method="POST",
            json={"response": "Hello from Ollama"},
        )
        client = OllamaClient(_ollama_config())
        try:
            result = await client.generate("Say hello")
            assert result == "Hello from Ollama"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:11434/api/generate",
            method="POST",
            json={"response": "I am a helpful assistant"},
        )
        client = OllamaClient(_ollama_config())
        try:
            result = await client.generate("Who are you?", system_prompt="You are helpful.")
            assert result == "I am a helpful assistant"

            request = httpx_mock.get_request()
            import json
            body = json.loads(request.content)
            assert body["system"] == "You are helpful."
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_chat(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:11434/api/chat",
            method="POST",
            json={"message": {"role": "assistant", "content": "Chat reply"}},
        )
        client = OllamaClient(_ollama_config())
        try:
            result = await client.chat([{"role": "user", "content": "Hi"}])
            assert result == "Chat reply"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_is_available_true(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            method="GET",
            json={"models": []},
        )
        client = OllamaClient(_ollama_config())
        try:
            assert await client.is_available() is True
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_is_available_false_on_error(self, httpx_mock):
        httpx_mock.add_exception(
            httpx.ConnectError("connection refused"),
            url="http://localhost:11434/api/tags",
        )
        client = OllamaClient(_ollama_config())
        try:
            assert await client.is_available() is False
        finally:
            await client.close()


# ---------------------------------------------------------------------------
# OpenAI-compatible provider tests
# ---------------------------------------------------------------------------

class TestOpenAICompatClient:
    @pytest.mark.asyncio
    async def test_chat(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8000/v1/chat/completions",
            method="POST",
            json={
                "choices": [{"message": {"role": "assistant", "content": "OpenAI reply"}}],
            },
        )
        client = OpenAICompatClient(_openai_config())
        try:
            result = await client.chat([{"role": "user", "content": "Hi"}])
            assert result == "OpenAI reply"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_generate_wraps_as_chat(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8000/v1/chat/completions",
            method="POST",
            json={
                "choices": [{"message": {"role": "assistant", "content": "Generated"}}],
            },
        )
        client = OpenAICompatClient(_openai_config())
        try:
            result = await client.generate("Do something", system_prompt="Be concise.")
            assert result == "Generated"

            import json
            request = httpx_mock.get_request()
            body = json.loads(request.content)
            assert body["messages"][0] == {"role": "system", "content": "Be concise."}
            assert body["messages"][1] == {"role": "user", "content": "Do something"}
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_is_available_true(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8000/v1/models",
            method="GET",
            json={"data": []},
        )
        client = OpenAICompatClient(_openai_config())
        try:
            assert await client.is_available() is True
        finally:
            await client.close()


# ---------------------------------------------------------------------------
# Health check tests
# ---------------------------------------------------------------------------

class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:11434/api/tags",
            method="GET",
            json={"models": []},
        )
        status = await check_llm_health(_ollama_config())
        assert isinstance(status, HealthStatus)
        assert status.healthy is True
        assert status.service == "llm:ollama"
        assert status.latency_ms is not None
        assert status.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_unhealthy(self, httpx_mock):
        httpx_mock.add_exception(
            httpx.ConnectError("refused"),
            url="http://localhost:11434/api/tags",
        )
        status = await check_llm_health(_ollama_config())
        assert status.healthy is False
