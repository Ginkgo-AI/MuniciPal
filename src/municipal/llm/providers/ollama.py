"""Ollama LLM provider using the Ollama REST API."""

from __future__ import annotations

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
            "options": {"temperature": temperature},
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
            "options": {"temperature": temperature},
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
        resp = await self._http.post(path, json=payload)
        resp.raise_for_status()
        return resp.json()
