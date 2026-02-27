# Munici-Pal

Sovereign AI orchestration layer for municipal government. Munici-Pal bridges the gap between complex regulations, legacy systems, and resident needs — while ensuring staff retain final authority over all legal, regulatory, and financial actions.

## What It Does

- **Residents** get a conversational assistant to navigate city services, apply for permits, file FOIA requests, and submit 311 tickets
- **Staff** get Mission Control: a real-time dashboard for session monitoring, approval queues, audit logs, and operational metrics
- **The system** enforces human-in-the-loop governance — AI proposes, staff disposes

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (Next.js)                 │
│  ┌──────────────────┐    ┌────────────────────────┐  │
│  │   Citizen Portal  │    │  Staff Mission Control │  │
│  │  Chat · Intake    │    │  Dashboard · Sessions  │  │
│  └────────┬─────────┘    └──────────┬─────────────┘  │
└───────────┼─────────────────────────┼────────────────┘
            │         REST API        │
┌───────────┴─────────────────────────┴────────────────┐
│                Backend (FastAPI)                      │
│                                                      │
│  RAG Pipeline ─── Chat Service ─── Intake Wizards    │
│  Finance Engine ── Approval Gates ── Review Engine    │
│  Legacy Bridge ─── Notifications ── Export (PDF/JSON) │
│  Graph Layer ──── GIS Integration ── i18n             │
│                                                      │
├──────────────────────────────────────────────────────┤
│  PostgreSQL 17  │  ChromaDB (vectors)  │  Ollama/vLLM │
└──────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy (async) |
| Frontend | Next.js 15, React 19, Tailwind CSS 4, TypeScript |
| Database | PostgreSQL 17, Alembic migrations |
| Vector DB | ChromaDB |
| LLM Runtime | Ollama or vLLM (self-hosted, default: `llama3.1:8b`) |
| Auth | NextAuth (staff), tiered sessions (citizen) |
| Monorepo | pnpm workspaces, Turborepo |
| PDF Generation | fpdf2 |
| Testing | pytest, pytest-asyncio |
| Linting | Ruff, MyPy (strict) |

## Prerequisites

- Python 3.11+
- Node.js 18+ and pnpm 9+
- Docker and Docker Compose
- (Optional) NVIDIA GPU for local LLM acceleration

## Getting Started

### 1. Clone and install dependencies

```bash
git clone <repo-url> && cd MuniciPal

# Python
pip install -e ".[postgres,dev]"

# Node
pnpm install
```

### 2. Start infrastructure

```bash
# Spins up PostgreSQL, ChromaDB, and Ollama; pulls the default LLM model
bash scripts/setup_infra.sh
```

Or manually with Docker Compose:

```bash
docker compose up -d
```

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start the backend

```bash
uvicorn municipal.web.app:create_app --factory --reload --port 8080
```

### 5. Start the frontend

```bash
pnpm dev
```

The citizen portal and staff dashboard will be available at the URLs printed by Next.js.

## Project Structure

```
MuniciPal/
├── apps/
│   ├── citizen/          # Resident-facing Next.js app (chat, intake)
│   └── staff/            # Staff Mission Control Next.js app
├── packages/
│   ├── api-client/       # Generated TypeScript API client
│   ├── ui/               # Shared React component library
│   └── tsconfig/         # Shared TypeScript configs
├── src/municipal/        # Python backend
│   ├── auth/             # Authentication & authorization
│   ├── bridge/           # Legacy system adapters
│   ├── chat/             # Conversational session management
│   ├── core/             # Configuration & utilities
│   ├── db/               # Database initialization
│   ├── eval/             # Model evaluation harness
│   ├── export/           # PDF/JSON export, Sunshine Reports
│   ├── finance/          # Deterministic fee/tax engine
│   ├── gis/              # Geographic information system
│   ├── governance/       # Approval gates & audit logging
│   ├── graph/            # Entity-relationship layer
│   ├── i18n/             # Internationalization
│   ├── intake/           # Permit/FOIA/311 intake wizards
│   ├── llm/              # LLM client (Ollama/vLLM)
│   ├── notifications/    # SMS/email notification engine
│   ├── rag/              # RAG pipeline with citations
│   ├── repositories/     # PostgreSQL data access layer
│   ├── review/           # Cross-field validation, FOIA redaction
│   ├── vectordb/         # Vector DB abstraction
│   └── web/              # FastAPI app, routers, Mission Control
├── config/               # YAML-driven configuration
│   ├── fee_schedules.yml
│   ├── deadline_rules.yml
│   ├── approval_policies.yml
│   ├── wizards/          # Intake wizard definitions
│   └── ...
├── tests/                # 560+ pytest tests
├── alembic/              # Database migrations
├── scripts/              # Setup and tooling scripts
├── docker-compose.yml
├── pyproject.toml
└── turbo.json
```

## Configuration

Munici-Pal is driven by YAML configuration files in `config/`:

| File | Purpose |
|------|---------|
| `fee_schedules.yml` | Municipal fee structures and calculation rules |
| `deadline_rules.yml` | Permit and application deadline logic |
| `approval_policies.yml` | Human-in-the-loop approval gate definitions |
| `cross_field_rules.yml` | Form-level validation rules |
| `redaction_rules.yml` | FOIA redaction patterns |
| `notification_templates.yml` | SMS/email templates |
| `bridge_adapters.yml` | Legacy system adapter configuration |
| `data_classification.yml` | Data sensitivity levels (Public/Internal/Restricted) |
| `wizards/` | Intake wizard step definitions |

## Running Tests

```bash
# All tests
python3 -m pytest tests/ -x -q

# Single file
python3 -m pytest tests/test_finance_fees.py -v

# With coverage
python3 -m pytest tests/ --cov=municipal --cov-report=term-missing
```

## Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup_infra.sh` | Stand up Docker services and pull LLM model |
| `scripts/generate-openapi.sh` | Export OpenAPI schema and generate TypeScript client |
| `scripts/run_eval.py` | Run the civic evaluation harness against golden datasets |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8080` | Backend API URL for frontend |
| `MUNICIPAL_LLM_MODEL` | `llama3.1:8b` | Ollama model to pull and use |
| `DATABASE_URL` | `postgresql+asyncpg://municipal:municipal_dev@localhost:5432/municipal` | PostgreSQL connection string |

## Design Principles

**Human-in-the-Loop** — No authoritative database writes without explicit staff approval. AI assists; humans decide.

**Data Sovereignty** — All data stays within municipal infrastructure. No external transmission of sensitive data.

**Deterministic Engines** — Fees, taxes, deadlines, and compliance math are computed by code, never delegated to an LLM.

**Auditability** — Every interaction is tied to a session ID, prompt version, tool calls, data sources, and approval chain.

**Graceful Degradation** — When retrieval confidence is low, the system routes to staff rather than guessing.

## License

MIT
