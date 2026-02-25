"""Load, validate, and manage golden evaluation datasets."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from municipal.core.types import EvalEntry


def load_dataset(path: str | Path) -> list[EvalEntry]:
    """Load a golden dataset from a JSON file.

    The file must contain a JSON array of objects matching the EvalEntry schema,
    or a JSON object with a top-level ``entries`` key holding such an array.

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the JSON is malformed or entries fail validation.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))

    # Accept either a bare list or {"entries": [...]}
    if isinstance(raw, dict):
        if "entries" not in raw:
            raise ValueError(
                "Dataset JSON object must contain an 'entries' key."
            )
        raw = raw["entries"]

    if not isinstance(raw, list):
        raise ValueError("Dataset must be a JSON array or object with 'entries' array.")

    entries: list[EvalEntry] = []
    errors: list[str] = []
    for idx, item in enumerate(raw):
        try:
            entries.append(EvalEntry.model_validate(item))
        except ValidationError as exc:
            errors.append(f"Entry {idx}: {exc}")

    if errors:
        raise ValueError(
            f"Dataset validation failed with {len(errors)} error(s):\n"
            + "\n".join(errors)
        )

    return entries


def validate_dataset(entries: list[EvalEntry]) -> list[str]:
    """Validate a list of EvalEntry objects and return a list of error strings.

    Returns an empty list when the dataset is valid.
    """
    errors: list[str] = []
    seen_ids: set[str] = set()

    valid_difficulties = {"easy", "medium", "hard"}
    for idx, entry in enumerate(entries):
        prefix = f"Entry {idx} (id={entry.id!r})"

        # Duplicate ID check.
        if entry.id in seen_ids:
            errors.append(f"{prefix}: duplicate id")
        seen_ids.add(entry.id)

        # Non-empty required text fields.
        if not entry.question.strip():
            errors.append(f"{prefix}: question is empty")
        if not entry.expected_answer.strip():
            errors.append(f"{prefix}: expected_answer is empty")
        if not entry.department.strip():
            errors.append(f"{prefix}: department is empty")
        if not entry.category.strip():
            errors.append(f"{prefix}: category is empty")

        # Difficulty in allowed set.
        if entry.difficulty not in valid_difficulties:
            errors.append(
                f"{prefix}: invalid difficulty {entry.difficulty!r}, "
                f"expected one of {sorted(valid_difficulties)}"
            )

    return errors
