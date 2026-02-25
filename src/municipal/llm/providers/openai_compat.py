"""OpenAI-compatible LLM provider (works with vLLM, llama-cpp-python, etc.)."""

from __future__ import annotations

import httpx

from municipal.core.config import LLMConfig
from municipal.llm.client import LLMClient


class OpenAICompatClient(LLMClient):
    """Talks to any server that exposes the OpenAI /v1/chat/completions API."""

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
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        resp = await self._http.post("/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def is_available(self) -> bool:
        try:
            r = await self._http.get("/v1/models")
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self._http.aclose()
