"""Ollama LLM provider using the Ollama REST API."""

from __future__ import annotations

import asyncio

import httpx

from municipal.core.config import LLMConfig
from municipal.llm.client import LLMClient


class OllamaClient(LLMClient):
    """Talks to a local Ollama instance."""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._http = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=httpx.Timeout(config.timeout_seconds),
        )
        self._max_retries = config.max_retries

    # -- public API ----------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        payload: dict = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096,
                "num_predict": 256,
            },
        }
        if system_prompt is not None:
            payload["system"] = system_prompt

        resp = await self._post("/api/generate", payload)
        return resp["response"]

    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.1,
    ) -> str:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096,
            },
        }
        resp = await self._post("/api/chat", payload)
        return resp["message"]["content"]

    async def is_available(self) -> bool:
        try:
            r = await self._http.get("/api/tags")
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self._http.aclose()

    # -- internal ------------------------------------------------------------

    async def _post(self, path: str, payload: dict) -> dict:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._http.post(path, json=payload)
                if resp.status_code >= 500 and attempt < self._max_retries:
                    last_exc = httpx.HTTPStatusError(
                        f"Server error {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                    await asyncio.sleep(2**attempt * 0.5)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(2**attempt * 0.5)
                    continue
                raise
        raise last_exc  # type: ignore[misc]
