"""Model management service for Ollama-backed LLM instances.

Provides model discovery, loading/unloading, memory management, system
resource detection, and resource-aware model recommendations — inspired
by LM Studio's model management UX.
"""

from __future__ import annotations

import logging
import platform
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx

from municipal.core.config import LLMConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model type classification
# ---------------------------------------------------------------------------


class ModelType(str, Enum):
    """Classification of model capabilities."""

    TEXT = "text"
    VISION = "vision"
    EMBEDDING = "embedding"
    CODE = "code"


# Families / name fragments that indicate embedding models
_EMBEDDING_FAMILIES = {"nomic-bert", "bert", "all-minilm", "snowflake-arctic-embed"}
_EMBEDDING_NAME_PATTERNS = ("embed", "e5-", "bge-", "gte-", "minilm", "sentence-")

# Families / name fragments that indicate vision models
_VISION_FAMILIES = {"llava", "bakllava", "moondream", "llava-llama3"}
_VISION_NAME_PATTERNS = ("llava", "vision", "moondream", "minicpm-v")

# Families / name fragments that indicate code-specialist models
_CODE_NAME_PATTERNS = ("codellama", "code-", "starcoder", "codestral", "codegemma")


def classify_model(name: str, family: str) -> ModelType:
    """Infer model type from its name and family metadata."""
    name_lower = name.lower()
    family_lower = family.lower()

    # Embedding check (highest priority — these can't chat)
    if family_lower in _EMBEDDING_FAMILIES:
        return ModelType.EMBEDDING
    if any(p in name_lower for p in _EMBEDDING_NAME_PATTERNS):
        return ModelType.EMBEDDING

    # Vision check
    if family_lower in _VISION_FAMILIES:
        return ModelType.VISION
    if any(p in name_lower for p in _VISION_NAME_PATTERNS):
        return ModelType.VISION

    # Code check
    if any(p in name_lower for p in _CODE_NAME_PATTERNS):
        return ModelType.CODE

    # Default: general text/chat model
    return ModelType.TEXT


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ModelInfo:
    """Metadata for a downloaded model."""

    name: str
    size_bytes: int = 0
    parameter_size: str = ""
    family: str = ""
    quantization: str = ""
    format: str = ""
    modified_at: str = ""
    digest: str = ""
    model_type: str = "text"
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def size_gb(self) -> float:
        return round(self.size_bytes / (1024**3), 2)

    @property
    def is_chat_capable(self) -> bool:
        return self.model_type in (ModelType.TEXT, ModelType.VISION, ModelType.CODE)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "size_bytes": self.size_bytes,
            "size_gb": self.size_gb,
            "parameter_size": self.parameter_size,
            "family": self.family,
            "quantization": self.quantization,
            "format": self.format,
            "modified_at": self.modified_at,
            "digest": self.digest,
            "model_type": self.model_type,
            "is_chat_capable": self.is_chat_capable,
        }


@dataclass
class LoadedModelInfo:
    """Metadata for a model currently loaded in memory."""

    name: str
    size_bytes: int = 0
    size_vram: int = 0
    context_length: int = 0
    expires_at: str = ""

    @property
    def size_gb(self) -> float:
        return round(self.size_bytes / (1024**3), 2)

    @property
    def vram_gb(self) -> float:
        return round(self.size_vram / (1024**3), 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "size_bytes": self.size_bytes,
            "size_gb": self.size_gb,
            "size_vram": self.size_vram,
            "vram_gb": self.vram_gb,
            "context_length": self.context_length,
            "expires_at": self.expires_at,
        }


@dataclass
class SystemResources:
    """System resource snapshot."""

    total_ram_bytes: int = 0
    available_ram_bytes: int = 0
    cpu_count: int = 0
    platform: str = ""
    gpu_available: bool = False
    gpu_name: str = ""

    @property
    def total_ram_gb(self) -> float:
        return round(self.total_ram_bytes / (1024**3), 2)

    @property
    def available_ram_gb(self) -> float:
        return round(self.available_ram_bytes / (1024**3), 2)

    @property
    def ram_usage_percent(self) -> float:
        if self.total_ram_bytes == 0:
            return 0.0
        used = self.total_ram_bytes - self.available_ram_bytes
        return round((used / self.total_ram_bytes) * 100, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_ram_bytes": self.total_ram_bytes,
            "total_ram_gb": self.total_ram_gb,
            "available_ram_bytes": self.available_ram_bytes,
            "available_ram_gb": self.available_ram_gb,
            "ram_usage_percent": self.ram_usage_percent,
            "cpu_count": self.cpu_count,
            "platform": self.platform,
            "gpu_available": self.gpu_available,
            "gpu_name": self.gpu_name,
        }


@dataclass
class ModelRecommendation:
    """A model recommendation with fit assessment."""

    model: ModelInfo
    fit: str  # "good", "moderate", "poor"
    reason: str
    score: float  # 0.0–1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model.to_dict(),
            "fit": self.fit,
            "reason": self.reason,
            "score": self.score,
        }


# ---------------------------------------------------------------------------
# ModelManager
# ---------------------------------------------------------------------------


class ModelManager:
    """Manages LLM models via the Ollama REST API.

    Provides discovery, loading, unloading, and resource-aware
    recommendations.
    """

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._http = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=httpx.Timeout(config.timeout_seconds),
        )

    # -- Discovery -----------------------------------------------------------

    async def list_available(self) -> list[ModelInfo]:
        """List all models downloaded on the Ollama server."""
        try:
            resp = await self._http.get("/api/tags")
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.error("Failed to list available models: %s", exc)
            return []

        models: list[ModelInfo] = []
        for m in data.get("models", []):
            details = m.get("details", {})
            name = m.get("name", "")
            family = details.get("family", "")
            model_type = classify_model(name, family)
            models.append(
                ModelInfo(
                    name=name,
                    size_bytes=m.get("size", 0),
                    parameter_size=details.get("parameter_size", ""),
                    family=family,
                    quantization=details.get("quantization_level", ""),
                    format=details.get("format", ""),
                    modified_at=m.get("modified_at", ""),
                    digest=m.get("digest", ""),
                    model_type=model_type.value,
                    details=details,
                )
            )
        return models

    async def list_loaded(self) -> list[LoadedModelInfo]:
        """List models currently loaded in memory."""
        try:
            resp = await self._http.get("/api/ps")
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.error("Failed to list loaded models: %s", exc)
            return []

        loaded: list[LoadedModelInfo] = []
        for m in data.get("models", []):
            loaded.append(
                LoadedModelInfo(
                    name=m.get("name", ""),
                    size_bytes=m.get("size", 0),
                    size_vram=m.get("size_vram", 0),
                    context_length=m.get("context_length", 0),
                    expires_at=m.get("expires_at", ""),
                )
            )
        return loaded

    async def show_model(self, name: str) -> dict[str, Any]:
        """Get detailed information about a specific model."""
        try:
            resp = await self._http.post("/api/show", json={"name": name})
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.error("Failed to show model %r: %s", name, exc)
            return {"error": str(exc)}

    # -- Loading / Unloading -------------------------------------------------

    async def load_model(
        self,
        name: str,
        *,
        keep_alive: str = "-1",
        num_ctx: int | None = None,
    ) -> dict[str, Any]:
        """Preload a model into memory.

        Sends a minimal generate request to trigger Ollama to load
        the model. Uses keep_alive=-1 (forever) by default.
        """
        payload: dict[str, Any] = {
            "model": name,
            "prompt": "",
            "stream": False,
            "keep_alive": keep_alive,
        }
        if num_ctx is not None:
            payload["options"] = {"num_ctx": num_ctx}

        try:
            resp = await self._http.post("/api/generate", json=payload)
            resp.raise_for_status()
            return {"status": "loaded", "model": name, "keep_alive": keep_alive}
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.error("Failed to load model %r: %s", name, exc)
            return {"status": "error", "model": name, "error": str(exc)}

    async def unload_model(self, name: str) -> dict[str, Any]:
        """Unload a model from memory by setting keep_alive to 0."""
        payload: dict[str, Any] = {
            "model": name,
            "prompt": "",
            "stream": False,
            "keep_alive": 0,
        }
        try:
            resp = await self._http.post("/api/generate", json=payload)
            resp.raise_for_status()
            return {"status": "unloaded", "model": name}
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.error("Failed to unload model %r: %s", name, exc)
            return {"status": "error", "model": name, "error": str(exc)}

    # -- System Resources ----------------------------------------------------

    @staticmethod
    def get_system_resources() -> SystemResources:
        """Detect system resources (RAM, CPU, GPU)."""
        try:
            import psutil

            mem = psutil.virtual_memory()
            total_ram = mem.total
            avail_ram = mem.available
            cpu_count = psutil.cpu_count(logical=True) or 0
        except ImportError:
            logger.warning("psutil not installed; falling back to platform defaults")
            import os

            cpu_count = os.cpu_count() or 0
            total_ram = 0
            avail_ram = 0

        # Basic GPU detection (Apple Silicon unified memory)
        gpu_available = False
        gpu_name = ""
        sys_platform = platform.system()
        if sys_platform == "Darwin":
            machine = platform.machine()
            if machine == "arm64":
                gpu_available = True
                gpu_name = "Apple Silicon (unified memory)"

        return SystemResources(
            total_ram_bytes=total_ram,
            available_ram_bytes=avail_ram,
            cpu_count=cpu_count,
            platform=f"{sys_platform} {platform.machine()}",
            gpu_available=gpu_available,
            gpu_name=gpu_name,
        )

    # -- Recommendations -----------------------------------------------------

    async def recommend_models(self) -> list[ModelRecommendation]:
        """Recommend models based on system resources.

        Compares each available model's size against available RAM
        and returns sorted recommendations (best fit first).
        """
        resources = self.get_system_resources()
        models = await self.list_available()

        if not models:
            return []

        available_ram = resources.available_ram_bytes
        recommendations: list[ModelRecommendation] = []

        for model in models:
            # Rough heuristic: model needs ~1.2× its file size in RAM
            estimated_ram = int(model.size_bytes * 1.2)

            if available_ram == 0:
                # Can't determine fit without RAM info
                recommendations.append(
                    ModelRecommendation(
                        model=model,
                        fit="unknown",
                        reason="System resource info unavailable",
                        score=0.5,
                    )
                )
                continue

            ratio = available_ram / max(estimated_ram, 1)

            if ratio >= 2.0:
                fit = "good"
                reason = (
                    f"Needs ~{round(estimated_ram / (1024**3), 1)} GB; "
                    f"you have {resources.available_ram_gb} GB free"
                )
                score = min(1.0, ratio / 3.0)
            elif ratio >= 1.0:
                fit = "moderate"
                reason = (
                    f"Needs ~{round(estimated_ram / (1024**3), 1)} GB; "
                    f"will use most of your {resources.available_ram_gb} GB free RAM"
                )
                score = ratio / 3.0
            else:
                fit = "poor"
                reason = (
                    f"Needs ~{round(estimated_ram / (1024**3), 1)} GB "
                    f"but only {resources.available_ram_gb} GB available"
                )
                score = max(0.0, ratio / 3.0)

            recommendations.append(
                ModelRecommendation(
                    model=model,
                    fit=fit,
                    reason=reason,
                    score=round(score, 3),
                )
            )

        # Sort: good first, then by score descending
        fit_order = {"good": 0, "moderate": 1, "unknown": 2, "poor": 3}
        recommendations.sort(
            key=lambda r: (fit_order.get(r.fit, 99), -r.score)
        )
        return recommendations

    # -- Cleanup -------------------------------------------------------------

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.aclose()
