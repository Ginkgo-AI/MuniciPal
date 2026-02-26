"""Tests for vLLM client enhancements (WP4)."""

from __future__ import annotations

import json

import httpx
import pytest

from municipal.core.config import LLMConfig
from municipal.llm.health import check_vllm_metrics
from municipal.llm.providers.openai_compat import OpenAICompatClient


def _vllm_config(**overrides) -> LLMConfig:
    defaults = {
        "provider": "vllm",
        "base_url": "http://localhost:8000",
        "model": "meta-llama/Llama-3-8B",
    }
    defaults.update(overrides)
    return LLMConfig(**defaults)


class TestAuthHeaderInjection:
    @pytest.mark.asyncio
    async def test_auth_header_present_when_api_key_set(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8000/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"role": "assistant", "content": "Hello"}}]},
        )
        config = _vllm_config(api_key="test-key-123")
        client = OpenAICompatClient(config)
        try:
            await client.chat([{"role": "user", "content": "Hi"}])
            request = httpx_mock.get_request()
            assert request.headers["authorization"] == "Bearer test-key-123"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_no_auth_header_when_no_api_key(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8000/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"role": "assistant", "content": "Hello"}}]},
        )
        config = _vllm_config()
        client = OpenAICompatClient(config)
        try:
            await client.chat([{"role": "user", "content": "Hi"}])
            request = httpx_mock.get_request()
            assert "authorization" not in request.headers
        finally:
            await client.close()


class TestMaxTokensInPayload:
    @pytest.mark.asyncio
    async def test_max_tokens_in_request(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8000/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"role": "assistant", "content": "Reply"}}]},
        )
        config = _vllm_config(max_tokens=4096)
        client = OpenAICompatClient(config)
        try:
            await client.chat([{"role": "user", "content": "Test"}])
            request = httpx_mock.get_request()
            body = json.loads(request.content)
            assert body["max_tokens"] == 4096
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_top_p_in_request(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8000/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"role": "assistant", "content": "Reply"}}]},
        )
        config = _vllm_config(top_p=0.9)
        client = OpenAICompatClient(config)
        try:
            await client.chat([{"role": "user", "content": "Test"}])
            request = httpx_mock.get_request()
            body = json.loads(request.content)
            assert body["top_p"] == 0.9
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_top_p_absent_when_none(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8000/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"role": "assistant", "content": "Reply"}}]},
        )
        config = _vllm_config()
        client = OpenAICompatClient(config)
        try:
            await client.chat([{"role": "user", "content": "Test"}])
            request = httpx_mock.get_request()
            body = json.loads(request.content)
            assert "top_p" not in body
        finally:
            await client.close()


class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retry_on_500(self, httpx_mock):
        # First request returns 500, second succeeds
        httpx_mock.add_response(
            url="http://localhost:8000/v1/chat/completions",
            method="POST",
            status_code=500,
        )
        httpx_mock.add_response(
            url="http://localhost:8000/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"role": "assistant", "content": "OK"}}]},
        )
        config = _vllm_config(max_retries=1)
        client = OpenAICompatClient(config)
        try:
            result = await client.chat([{"role": "user", "content": "Hi"}])
            assert result == "OK"
            assert len(httpx_mock.get_requests()) == 2
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_no_retry_on_400(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8000/v1/chat/completions",
            method="POST",
            status_code=400,
            json={"error": "bad request"},
        )
        config = _vllm_config(max_retries=2)
        client = OpenAICompatClient(config)
        try:
            with pytest.raises(httpx.HTTPStatusError):
                await client.chat([{"role": "user", "content": "Hi"}])
            # Only one request should have been made
            assert len(httpx_mock.get_requests()) == 1
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_retry_on_transport_error(self, httpx_mock):
        httpx_mock.add_exception(
            httpx.ConnectError("connection refused"),
            url="http://localhost:8000/v1/chat/completions",
        )
        httpx_mock.add_response(
            url="http://localhost:8000/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"role": "assistant", "content": "OK"}}]},
        )
        config = _vllm_config(max_retries=1)
        client = OpenAICompatClient(config)
        try:
            result = await client.chat([{"role": "user", "content": "Hi"}])
            assert result == "OK"
        finally:
            await client.close()


class TestGetModelInfo:
    @pytest.mark.asyncio
    async def test_get_model_info(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8000/v1/models",
            method="GET",
            json={"data": [{"id": "meta-llama/Llama-3-8B", "object": "model"}]},
        )
        config = _vllm_config()
        client = OpenAICompatClient(config)
        try:
            info = await client.get_model_info()
            assert "data" in info
            assert info["data"][0]["id"] == "meta-llama/Llama-3-8B"
        finally:
            await client.close()


class TestVLLMMetrics:
    @pytest.mark.asyncio
    async def test_check_vllm_metrics_healthy(self, httpx_mock):
        metrics_text = (
            "# HELP vllm:num_requests_running Number of running requests\n"
            "vllm:num_requests_running 5\n"
            "# HELP vllm:num_requests_waiting Number of waiting requests\n"
            "vllm:num_requests_waiting 2\n"
            "# HELP vllm:gpu_cache_usage_perc GPU cache usage\n"
            "vllm:gpu_cache_usage_perc 0.45\n"
        )
        httpx_mock.add_response(
            url="http://localhost:8000/metrics",
            method="GET",
            text=metrics_text,
        )
        config = _vllm_config()
        result = await check_vllm_metrics(config)
        assert result["healthy"] is True
        assert result["num_requests_running"] == 5.0
        assert result["num_requests_waiting"] == 2.0
        assert result["gpu_cache_usage_perc"] == 0.45

    @pytest.mark.asyncio
    async def test_check_vllm_metrics_unhealthy(self, httpx_mock):
        httpx_mock.add_exception(
            httpx.ConnectError("connection refused"),
            url="http://localhost:8000/metrics",
        )
        config = _vllm_config()
        result = await check_vllm_metrics(config)
        assert result["healthy"] is False
        assert "error" in result
