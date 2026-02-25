"""Main evaluation runner implementing LLM-as-judge grading."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from municipal.core.config import EvalConfig
from municipal.core.types import EvalEntry, EvalResult
from municipal.eval.metrics import EvalMetrics, compute_metrics
from municipal.llm.client import LLMClient

# ---------------------------------------------------------------------------
# Prompt used for LLM-as-judge grading
# ---------------------------------------------------------------------------
JUDGE_SYSTEM_PROMPT = (
    "You are an evaluation judge for a municipal government AI assistant. "
    "Compare the generated answer against the expected answer and return a "
    "JSON object with the following keys:\n"
    '  "accurate": true/false — whether the generated answer is factually '
    "consistent with the expected answer,\n"
    '  "hallucination": true/false — whether the generated answer contains '
    "claims not supported by the expected answer,\n"
    '  "reasoning": a brief explanation of your judgement.\n'
    "Respond with ONLY valid JSON, no other text."
)

JUDGE_USER_TEMPLATE = (
    "Expected answer:\n{expected}\n\n"
    "Generated answer:\n{generated}\n\n"
    "Evaluate the generated answer against the expected answer."
)

# ---------------------------------------------------------------------------
# Citation extraction patterns
# ---------------------------------------------------------------------------
_CITATION_PATTERNS = [
    re.compile(r"\[Source:\s*(.+?)\]", re.IGNORECASE),
    re.compile(r"\[Ref:\s*(.+?)\]", re.IGNORECASE),
    re.compile(r"\[Citation:\s*(.+?)\]", re.IGNORECASE),
]


def extract_citations(text: str) -> list[str]:
    """Extract cited sources from LLM output text."""
    sources: list[str] = []
    for pattern in _CITATION_PATTERNS:
        sources.extend(pattern.findall(text))
    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for s in sources:
        normed = s.strip()
        if normed and normed not in seen:
            seen.add(normed)
            unique.append(normed)
    return unique


def _citation_precision(cited: list[str], expected: list[str]) -> float:
    """Fraction of cited sources that appear in expected sources."""
    if not cited:
        return 1.0  # No citations made — nothing wrong cited.
    expected_lower = {s.lower() for s in expected}
    correct = sum(1 for c in cited if c.lower() in expected_lower)
    return correct / len(cited)


def _citation_recall(cited: list[str], expected: list[str]) -> float:
    """Fraction of expected sources that were cited."""
    if not expected:
        return 1.0  # Nothing to cite.
    cited_lower = {c.lower() for c in cited}
    found = sum(1 for e in expected if e.lower() in cited_lower)
    return found / len(expected)


# ---------------------------------------------------------------------------
# Report model
# ---------------------------------------------------------------------------
class EvalReport(BaseModel):
    """Complete evaluation report."""

    results: list[EvalResult] = Field(default_factory=list)
    metrics: EvalMetrics = Field(default_factory=EvalMetrics)
    config: EvalConfig = Field(default_factory=EvalConfig)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    model_id: str = ""


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------
class EvalHarness:
    """Run a golden-dataset evaluation against an LLM."""

    def __init__(self, client: LLMClient, config: EvalConfig | None = None) -> None:
        self.client = client
        self.config = config or EvalConfig()

    async def _judge_answer(
        self, generated: str, expected: str
    ) -> tuple[bool, bool]:
        """Use the LLM as a judge to assess answer accuracy.

        Returns (accurate, hallucination).
        """
        prompt = JUDGE_USER_TEMPLATE.format(
            expected=expected, generated=generated
        )
        try:
            raw = await self.client.generate(
                prompt,
                system_prompt=JUDGE_SYSTEM_PROMPT,
                temperature=0.0,
            )
            # Try to parse the JSON verdict from the response.
            # Strip markdown code fences if present.
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)
            verdict = json.loads(cleaned)
            accurate = bool(verdict.get("accurate", False))
            hallucination = bool(verdict.get("hallucination", False))
            return accurate, hallucination
        except (json.JSONDecodeError, Exception):
            # If the judge fails to produce valid JSON, be conservative.
            return False, False

    async def _evaluate_entry(self, entry: EvalEntry) -> EvalResult:
        """Evaluate a single dataset entry."""
        start = time.perf_counter()
        generated = await self.client.generate(entry.question)
        latency_ms = (time.perf_counter() - start) * 1000.0

        cited = extract_citations(generated)
        accurate, hallucination = await self._judge_answer(
            generated, entry.expected_answer
        )

        cp = _citation_precision(cited, entry.expected_sources)
        cr = _citation_recall(cited, entry.expected_sources)

        return EvalResult(
            entry_id=entry.id,
            question=entry.question,
            generated_answer=generated,
            expected_answer=entry.expected_answer,
            cited_sources=cited,
            expected_sources=entry.expected_sources,
            answer_accurate=accurate,
            citation_precision=round(cp, 4),
            citation_recall=round(cr, 4),
            contains_hallucination=hallucination,
            correctly_refused=False,
            latency_ms=round(latency_ms, 2),
        )

    async def run(self, dataset: list[EvalEntry]) -> EvalReport:
        """Run the evaluation harness over a full dataset."""
        results: list[EvalResult] = []
        for entry in dataset:
            result = await self._evaluate_entry(entry)
            results.append(result)

        metrics = compute_metrics(results, self.config)

        return EvalReport(
            results=results,
            metrics=metrics,
            config=self.config,
            timestamp=datetime.now(timezone.utc),
            model_id=self.client.config.model,
        )
