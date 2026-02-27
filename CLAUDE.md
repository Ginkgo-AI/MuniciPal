# CLAUDE.md — Munici-Pal

Sovereign AI orchestration layer for municipal government: RAG chat assistant, intake wizards, finance engines, staff Mission Control.

## Commands

```bash
python3 -m pytest tests/ -x -q          # run all tests (use python3, not python)
python3 -m pytest tests/test_foo.py -v   # run one test file
```

## Project Layout

- `src/municipal/` — all source code (core, llm, rag, chat, intake, finance, governance, bridge, export, web)
- `tests/` — flat test directory, all `test_*.py` files
- `config/` — YAML config files (fee_schedules, deadline_rules, approval_gates, etc.)

## Key Patterns

- **App state injection** via `request.app.state` — NOT FastAPI Depends
- **In-memory stores** (dict/list based) for sessions, payments, feedback, comparisons
- **YAML-driven config** for fee schedules, deadline rules, approval gates
- **Deterministic engines** for finance (zero LLM calls)
- **DataClassification** enum (PUBLIC, INTERNAL, RESTRICTED) — financial models are always RESTRICTED
- **Approval gates** for HITL decisions (payment_refund, data_export, etc.)
- `from __future__ import annotations` in every file
- `str | None` syntax (not `Optional[str]`)

## Gotchas

- YAML parses `311` as int — always cast with `str(wizard_type)` when using YAML keys
- `CitedAnswer` lives at `municipal.rag.citation`, not `municipal.rag.models`
- fpdf2 `pdf.output()` returns `bytearray`, not `bytes` — use `isinstance(result, (bytes, bytearray))`
- Never expose `api_key` in API responses — use `model_dump(exclude={"api_key"})`
- Never fabricate fallback values for financial calculations — raise ValueError instead
- Use `None` (not `0.0`) as sentinel for computed fields like subtotal/total
- All datetimes should use `timezone.utc` — never use naive `datetime.now()` or `date.today()`

## Security Rules

- Never return raw exception messages to clients (information disclosure)
- Staff endpoints (`/api/staff/*`) require auth checks — do not add unauthenticated staff routes
- CORS origins must be explicit when `allow_credentials=True` — never use `["*"]`
- Use SHA-256 for integrity hashing (not MD5)
- Validate and compile regex patterns loaded from config (ReDoS risk)
- Store `asyncio.create_task()` references to prevent GC — use a `set` with `add_done_callback`

## Workflow Rules

- **Always run `/pr-review-toolkit:review-pr` BEFORE committing** after completing substantial work. Fix critical and important findings before creating the commit. Do not wait for the user to ask for a review.
- When implementing a multi-WP plan, review after completing all WPs but before committing.
- Run tests after every set of changes.
