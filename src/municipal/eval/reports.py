"""Format and export evaluation reports."""

from __future__ import annotations

import json
from pathlib import Path

from municipal.eval.harness import EvalReport


def _pass_fail(value: float, target: float, *, lower_is_better: bool = False) -> str:
    """Return a PASS/FAIL indicator string."""
    if lower_is_better:
        ok = value <= target
    else:
        ok = value >= target
    mark = "PASS" if ok else "FAIL"
    return mark


def format_report(report: EvalReport) -> str:
    """Produce a human-readable text summary of an EvalReport."""
    m = report.metrics
    c = report.config
    lines: list[str] = []

    lines.append("=" * 64)
    lines.append("  Munici-Pal Evaluation Report")
    lines.append("=" * 64)
    lines.append(f"  Timestamp : {report.timestamp.isoformat()}")
    lines.append(f"  Model     : {report.model_id}")
    lines.append(f"  Entries   : {m.total_entries}")
    overall = "PASS" if m.passing else "FAIL"
    lines.append(f"  Overall   : {overall}")
    lines.append("-" * 64)
    lines.append("  Metric                     Value      Target     Status")
    lines.append("-" * 64)

    rows = [
        ("Answer accuracy", f"{m.answer_accuracy:.2%}", f">= {c.accuracy_target:.0%}",
         _pass_fail(m.answer_accuracy, c.accuracy_target)),
        ("Citation precision", f"{m.citation_precision:.2%}", f">= {c.citation_precision_target:.0%}",
         _pass_fail(m.citation_precision, c.citation_precision_target)),
        ("Citation recall", f"{m.citation_recall:.2%}", f">= {c.citation_recall_target:.0%}",
         _pass_fail(m.citation_recall, c.citation_recall_target)),
        ("Hallucination rate", f"{m.hallucination_rate:.2%}", f"<= {c.hallucination_max:.0%}",
         _pass_fail(m.hallucination_rate, c.hallucination_max, lower_is_better=True)),
        ("Refusal rate", f"{m.refusal_rate:.2%}", f">= {c.refusal_rate_target:.0%}",
         _pass_fail(m.refusal_rate, c.refusal_rate_target)),
        ("Latency p50", f"{m.latency_p50_ms:.0f} ms", f"<= {c.latency_p50_target_ms:.0f} ms",
         _pass_fail(m.latency_p50_ms, c.latency_p50_target_ms, lower_is_better=True)),
        ("Latency p95", f"{m.latency_p95_ms:.0f} ms", f"<= {c.latency_p95_target_ms:.0f} ms",
         _pass_fail(m.latency_p95_ms, c.latency_p95_target_ms, lower_is_better=True)),
    ]

    for name, value, target, status in rows:
        lines.append(f"  {name:<26} {value:<10} {target:<10} {status}")

    lines.append("=" * 64)
    return "\n".join(lines)


def export_report(report: EvalReport, path: str | Path) -> None:
    """Save an EvalReport to a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = report.model_dump(mode="json")
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
