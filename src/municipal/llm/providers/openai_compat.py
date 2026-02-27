"""OpenAI-compatible LLM provider (works with vLLM, llama-cpp-python, etc.)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from municipal.core.config import LLMConfig
from municipal.llm.client import LLMClient

logger = logging.getLogger(__name__)


class OpenAICompatClient(LLMClient):
    """Talks to any server that exposes the OpenAI /v1/chat/completions API."""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        headers: dict[str, str] = {}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        self._http = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=httpx.Timeout(config.timeout_seconds),
            headers=headers,
        )

    # -- public API ----------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        messages: list[dict] = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return await self.chat(messages, temperature=temperature)

    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.1,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            "max_tokens": self.config.max_tokens,
        }
        if self.config.top_p is not None:
            payload["top_p"] = self.config.top_p

        resp = await self._request_with_retry("POST", "/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def is_available(self) -> bool:
        try:
            r = await self._http.get("/v1/models")
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def get_model_info(self) -> dict[str, Any]:
        """Fetch model info from the /v1/models endpoint."""
        resp = await self._http.get("/v1/models")
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._http.aclose()

    # -- internal retry logic ------------------------------------------------

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute an HTTP request with retry on 5xx and transport errors."""
        max_attempts = max(1, self.config.max_retries + 1)
        last_resp: httpx.Response | None = None

        for attempt in range(max_attempts):
            try:
                resp = await self._http.request(method, url, **kwargs)
                # Don't retry on client errors (4xx)
                if resp.status_code < 500:
                    return resp
                last_resp = resp
                # Retry on 5xx
                if attempt < max_attempts - 1:
                    delay = 0.5 * (2 ** attempt)
                    logger.warning(
                        "Request to %s returned %d, retrying in %.1fs (%d/%d)",
                        url, resp.status_code, delay, attempt + 1, max_attempts,
                    )
                    await asyncio.sleep(delay)
                    continue
                return resp
            except httpx.TransportError as exc:
                if attempt < max_attempts - 1:
                    delay = 0.5 * (2 ** attempt)
                    logger.warning(
                        "Transport error on %s: %s, retrying in %.1fs (%d/%d)",
                        url, exc, delay, attempt + 1, max_attempts,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        return last_resp  # type: ignore[return-value]
