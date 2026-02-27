"""Health check for the configured LLM provider."""

from __future__ import annotations

import time
from typing import Any

import httpx

from municipal.core.config import LLMConfig
from municipal.core.types import HealthStatus
from municipal.llm.client import create_llm_client


async def check_llm_health(config: LLMConfig) -> HealthStatus:
    """Probe the LLM backend and return a HealthStatus."""

    client = create_llm_client(config)
    try:
        start = time.monotonic()
        available = await client.is_available()
        latency_ms = (time.monotonic() - start) * 1000

        return HealthStatus(
            service=f"llm:{config.provider}",
            healthy=available,
            latency_ms=round(latency_ms, 2),
            details={
                "base_url": config.base_url,
                "model": config.model,
            },
        )
    except Exception as exc:
        return HealthStatus(
            service=f"llm:{config.provider}",
            healthy=False,
            details={"error": str(exc)},
        )
    finally:
        await client.close()


async def check_vllm_metrics(config: LLMConfig) -> dict[str, Any]:
    """Scrape the Prometheus /metrics endpoint from a vLLM server.

    Returns a dict with raw metrics text and parsed key metrics.
    """
    headers: dict[str, str] = {}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    async with httpx.AsyncClient(
        base_url=config.base_url,
        timeout=httpx.Timeout(config.timeout_seconds),
        headers=headers,
    ) as client:
        try:
            resp = await client.get("/metrics")
            resp.raise_for_status()
            raw = resp.text
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            return {"healthy": False, "error": str(exc)}

        metrics: dict[str, Any] = {"raw": raw, "healthy": True}
        for line in raw.splitlines():
            if line.startswith("#"):
                continue
            if "vllm:num_requests_running" in line:
                parts = line.split()
                if len(parts) >= 2:
                    metrics["num_requests_running"] = float(parts[-1])
            elif "vllm:num_requests_waiting" in line:
                parts = line.split()
                if len(parts) >= 2:
                    metrics["num_requests_waiting"] = float(parts[-1])
            elif "vllm:gpu_cache_usage_perc" in line:
                parts = line.split()
                if len(parts) >= 2:
                    metrics["gpu_cache_usage_perc"] = float(parts[-1])

        return metrics
