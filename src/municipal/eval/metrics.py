"""Compute aggregate evaluation metrics from individual results."""

from __future__ import annotations

import statistics

from pydantic import BaseModel

from municipal.core.config import EvalConfig
from municipal.core.types import EvalResult


class EvalMetrics(BaseModel):
    """Aggregated evaluation metrics computed from a list of EvalResult."""

    answer_accuracy: float = 0.0
    citation_precision: float = 0.0
    citation_recall: float = 0.0
    hallucination_rate: float = 0.0
    refusal_rate: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    total_entries: int = 0
    passing: bool = False


def _percentile(values: list[float], pct: float) -> float:
    """Compute a percentile from a sorted list of values."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_vals):
        return sorted_vals[f]
    return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])


def compute_metrics(
    results: list[EvalResult],
    config: EvalConfig | None = None,
) -> EvalMetrics:
    """Compute aggregate EvalMetrics from a list of EvalResult.

    If *config* is provided the ``passing`` flag is set based on the
    configured targets; otherwise it defaults to ``False``.
    """
    if not results:
        return EvalMetrics(total_entries=0)

    n = len(results)

    accuracy = sum(1 for r in results if r.answer_accurate) / n
    cit_precision = statistics.mean([r.citation_precision for r in results])
    cit_recall = statistics.mean([r.citation_recall for r in results])
    hallucination = sum(1 for r in results if r.contains_hallucination) / n
    refusal = sum(1 for r in results if r.correctly_refused) / n

    latencies = [r.latency_ms for r in results]
    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)

    passing = False
    if config is not None:
        passing = (
            accuracy >= config.accuracy_target
            and cit_precision >= config.citation_precision_target
            and cit_recall >= config.citation_recall_target
            and hallucination <= config.hallucination_max
            and p50 <= config.latency_p50_target_ms
            and p95 <= config.latency_p95_target_ms
        )

    return EvalMetrics(
        answer_accuracy=round(accuracy, 4),
        citation_precision=round(cit_precision, 4),
        citation_recall=round(cit_recall, 4),
        hallucination_rate=round(hallucination, 4),
        refusal_rate=round(refusal, 4),
        latency_p50_ms=round(p50, 2),
        latency_p95_ms=round(p95, 2),
        total_entries=n,
        passing=passing,
    )
