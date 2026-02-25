"""Health check for the configured LLM provider."""

from __future__ import annotations

import time

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
