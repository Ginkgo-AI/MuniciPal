#!/usr/bin/env python3
"""CLI script to run the Munici-Pal evaluation harness."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure the project source is importable when running the script directly.
_project_root = Path(__file__).resolve().parent.parent
_src = _project_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from municipal.core.config import EvalConfig, Settings  # noqa: E402
from municipal.eval.golden_dataset import load_dataset, validate_dataset  # noqa: E402
from municipal.eval.harness import EvalHarness  # noqa: E402
from municipal.eval.reports import export_report, format_report  # noqa: E402
from municipal.llm.client import create_llm_client  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Munici-Pal evaluation harness against a golden dataset."
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(_project_root / "eval" / "golden_datasets" / "sample.json"),
        help="Path to the golden dataset JSON file.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to write the JSON evaluation report.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    # Load settings from environment.
    settings = Settings()
    eval_config: EvalConfig = settings.eval

    # Load and validate dataset.
    print(f"Loading dataset from {args.dataset} ...")
    dataset = load_dataset(args.dataset)
    errors = validate_dataset(dataset)
    if errors:
        print("Dataset validation errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    print(f"Loaded {len(dataset)} entries.")

    # Create LLM client.
    client = create_llm_client(settings.llm)

    # Confirm the model is reachable.
    if not await client.is_available():
        print(f"ERROR: LLM provider '{settings.llm.provider}' is not reachable.")
        sys.exit(1)

    # Run the evaluation.
    harness = EvalHarness(client, eval_config)
    print("Running evaluation ...")
    report = await harness.run(dataset)

    # Print the text report.
    print()
    print(format_report(report))

    # Export if requested.
    if args.output:
        export_report(report, args.output)
        print(f"\nReport exported to {args.output}")

    # Clean up.
    await client.close()

    # Exit code reflects pass/fail.
    sys.exit(0 if report.metrics.passing else 1)


if __name__ == "__main__":
    asyncio.run(main())
