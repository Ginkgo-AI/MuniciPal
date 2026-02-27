# Munici-Pal — IT Technical Reference

This document is intended for IT officers evaluating Munici-Pal for deployment in a municipal environment. It covers architecture, infrastructure requirements, security posture, integration patterns, and operational procedures.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Infrastructure Requirements](#infrastructure-requirements)
3. [Security and Compliance](#security-and-compliance)
4. [Data Architecture](#data-architecture)
5. [LLM Hosting and Model Management](#llm-hosting-and-model-management)
6. [Integration with Legacy Systems](#integration-with-legacy-systems)
7. [Authentication and Identity](#authentication-and-identity)
8. [Deployment and Operations](#deployment-and-operations)
9. [Monitoring and Observability](#monitoring-and-observability)
10. [Disaster Recovery and Data Retention](#disaster-recovery-and-data-retention)

---

## 1. System Architecture

Munici-Pal is a three-tier application consisting of a Next.js frontend, a Python/FastAPI backend, and a data layer comprising PostgreSQL, ChromaDB, and a self-hosted LLM runtime.

```
                       ┌──────────────┐   ┌──────────────┐
                       │   Citizen    │   │    Staff     │
                       │   Portal     │   │   Mission    │
                       │  (Next.js)   │   │   Control    │
                       └──────┬───────┘   └──────┬───────┘
                              │    HTTPS / WSS    │
                       ┌──────┴──────────────────┴───────┐
                       │        API Gateway / Reverse     │
                       │             Proxy                │
                       └──────────────┬──────────────────┘
                                      │
                       ┌──────────────┴──────────────────┐
                       │     FastAPI Backend (Python)     │
                       │                                  │
                       │  ┌────────┐ ┌────────┐ ┌──────┐ │
                       │  │  RAG   │ │ Intake │ │ Chat │ │
                       │  │Pipeline│ │Wizards │ │Svc   │ │
                       │  └────────┘ └────────┘ └──────┘ │
                       │  ┌────────┐ ┌────────┐ ┌──────┐ │
                       │  │Finance │ │Approval│ │Review│ │
                       │  │Engine  │ │ Gates  │ │Engine│ │
                       │  └────────┘ └────────┘ └──────┘ │
                       │  ┌────────┐ ┌────────┐ ┌──────┐ │
                       │  │ Bridge │ │ Export │ │ GIS  │ │
                       │  │Adapters│ │PDF/JSON│ │      │ │
                       │  └────────┘ └────────┘ └──────┘ │
                       └──┬──────────┬───────────┬───────┘
                          │          │           │
              ┌───────────┴──┐ ┌─────┴─────┐ ┌──┴──────────┐
              │ PostgreSQL   │ │ ChromaDB  │ │ Ollama/vLLM │
              │ 17           │ │ (vectors) │ │ (LLM)       │
              └──────────────┘ └───────────┘ └─────────────┘
```

### Component Summary

| Component | Technology | Role |
|-----------|-----------|------|
| Citizen Portal | Next.js 15, React 19, TypeScript | Resident-facing chat and intake UI |
| Staff Portal | Next.js 15, React 19, NextAuth | Mission Control dashboard |
| API Backend | Python 3.11+, FastAPI, Pydantic v2 | Business logic, API layer |
| Relational DB | PostgreSQL 17, SQLAlchemy (async), Alembic | Sessions, cases, payments, audit logs |
| Vector DB | ChromaDB | Document embeddings for RAG retrieval |
| LLM Runtime | Ollama or vLLM | Self-hosted language model inference |
| Shared Packages | TypeScript, pnpm workspaces, Turborepo | UI components, API client, config |

### Monorepo Layout

The codebase uses a pnpm workspace monorepo managed by Turborepo:

```
apps/citizen        → Resident portal (Next.js)
apps/staff          → Staff dashboard (Next.js)
packages/api-client → Auto-generated TypeScript API client from OpenAPI
packages/ui         → Shared React component library
packages/tsconfig   → Shared TypeScript configuration
src/municipal/      → Python backend (22+ modules)
config/             → YAML business rule configuration
tests/              → 560+ pytest tests
alembic/            → PostgreSQL schema migrations
```

---

## 2. Infrastructure Requirements

### Minimum Hardware

| Resource | Specification |
|----------|--------------|
| CPU | 8 cores (backend + frontend + database) |
| RAM | 32 GB minimum (16 GB for LLM, 8 GB for services, 8 GB for DB/vector) |
| GPU | NVIDIA GPU with 8+ GB VRAM recommended for LLM inference (optional — CPU inference supported) |
| Storage | 100 GB SSD (database, vector store, model weights, audit logs) |

### Software Dependencies

| Dependency | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend build and runtime |
| pnpm | 9+ | Package management |
| PostgreSQL | 17 | Relational data store |
| Docker / Docker Compose | Latest stable | Container orchestration |
| Ollama or vLLM | Latest stable | LLM model serving |

### Network Requirements

| Port | Service | Access |
|------|---------|--------|
| 443 | Frontend (via reverse proxy) | Public (residents and staff) |
| 8080 | FastAPI backend | Internal (frontend only) |
| 5432 | PostgreSQL | Internal (backend only) |
| 8000 | ChromaDB | Internal (backend only) |
| 11434 | Ollama | Internal (backend only) |

All inter-service communication is internal. Only the reverse proxy endpoint is exposed externally.

---

## 3. Security and Compliance

### Data Sovereignty

All data processing occurs within municipal infrastructure. The system supports:

- **Fully offline / air-gapped** deployments
- **On-premises GPU servers** for LLM inference
- **No external API calls** for core functionality (LLM, vector search, database)

No resident data, conversation logs, embeddings, or audit records leave the municipal network boundary.

### Data Classification

Every piece of data flowing through the system is tagged with a classification level that drives access control, caching, and logging behavior:

| Level | Caching | Logging | Access Control |
|-------|---------|---------|---------------|
| Public | Allowed | Standard | Open |
| Internal | Session-scoped | Standard | Staff only |
| Sensitive | Session-scoped, encrypted | Enhanced (PII redacted in logs) | Role-based |
| Restricted | Prohibited | Full audit, access-logged | Role-based + approval required |

Financial data is always classified Restricted. Resident-submitted attachments default to Sensitive until reviewed.

### Authentication

**Staff portal:** NextAuth-based authentication with username and verification code. Supports integration with municipal SSO (SAML/OIDC).

**Citizen portal:** Three-tiered session model:

| Tier | Capabilities | Identity Assurance |
|------|-------------|-------------------|
| Anonymous | Knowledge queries, general information | None |
| Verified | Intake submissions, case tracking | Light verification (email) |
| Authenticated | FOIA tracking, payments, case history | Full authentication |

Sessions upgrade gracefully from anonymous to authenticated as needed — residents are never forced to log in for basic questions.

### Audit Trail

All actions are logged to an append-only, SHA-256 integrity-hashed audit store:

- Session ID and actor identity
- Every LLM prompt and response
- Every tool call with input/output
- Data sources cited in responses
- Approval gate decisions with justifications
- Timestamps (UTC)

Audit logs may themselves be subject to public records requests and are stored in compliance with municipal retention policies.

### Application Security

- CORS configured with explicit origin allowlists (no wildcard with credentials)
- Staff endpoints require authentication — no unauthenticated staff routes
- Raw exception messages are never exposed to clients
- API keys and secrets are excluded from all API responses
- Regex patterns loaded from config are validated and compiled to prevent ReDoS
- Background tasks are properly reference-held to prevent garbage collection
- PDF generation handles `bytearray` output correctly

### Prompt Injection Defense

- All resident-submitted content and attachments are treated as untrusted
- Tool execution cannot be triggered by content within untrusted inputs
- The system enforces policy guardrails between the LLM and any tool calls

---

## 4. Data Architecture

### PostgreSQL 17

Primary relational store for structured data:

- **Sessions** — chat session metadata and state
- **Cases** — permit applications, FOIA requests, 311 tickets
- **Payments** — financial transaction records
- **Audit logs** — append-only event log
- **User accounts** — staff and resident identity records

Schema managed via Alembic migrations with async PostgreSQL driver (`asyncpg`).

### ChromaDB

Vector database for the RAG (Retrieval-Augmented Generation) pipeline:

- Stores document embeddings for ordinances, FAQs, fee schedules, SOPs
- Queried at inference time to ground LLM responses in source documents
- Supports document versioning and metadata filtering
- Data resides on local storage — no external vector DB service

### Entity Relationship Graph

In-memory graph layer modeling relationships between:

- Parcels and property owners
- Permits and inspections
- Contractors and licenses
- Cases and documents
- Residents, cases, and departments

Enables cross-entity lookups without querying multiple legacy systems.

---

## 5. LLM Hosting and Model Management

### Supported Runtimes

| Runtime | GPU Required | Use Case |
|---------|-------------|----------|
| Ollama | Optional (CPU fallback) | Development and smaller deployments |
| vLLM | Recommended | Production with higher throughput |

Both runtimes expose an OpenAI-compatible API, so the backend is runtime-agnostic.

### Default Model

`llama3.1:8b` — configurable via the `MUNICIPAL_LLM_MODEL` environment variable. Any model compatible with the runtime can be substituted.

### Model Evaluation Harness

Before deploying a new model, run it against the civic evaluation harness:

```bash
python3 scripts/run_eval.py --dataset path/to/golden_dataset.json
```

The harness measures:

| Metric | Target |
|--------|--------|
| Answer accuracy (semantic match) | > 90% |
| Citation precision | > 95% |
| Citation recall | > 85% |
| Hallucination rate | < 5% |
| Correct refusals (no source available) | > 90% |
| Median latency (p50) | < 3 seconds |
| 95th percentile latency | < 8 seconds |

The harness should be re-run on model upgrades, prompt changes, and knowledge base updates.

### Deterministic Engines

Sensitive calculations are never delegated to the LLM:

| Handled by Code | Handled by LLM |
|-----------------|----------------|
| Fee calculations | Natural language generation |
| Deadline computation | Reasoning assistance |
| Compliance math | Summarization |
| Tax calculations | Guidance and Q&A |

The finance engine computes fees from YAML-defined schedules using deterministic arithmetic. If a calculation cannot be completed, the system raises an error rather than fabricating a value.

---

## 6. Integration with Legacy Systems

### Bridge Adapter Pattern

```
Legacy System → Bridge Adapter → Normalized JSON → Backend
```

Each adapter handles:

- **Protocol translation** — SOAP/XML, ODBC/SQL, REST, FTP, or proprietary protocols normalized to JSON
- **Schema normalization** — vendor-specific fields mapped to canonical internal schema
- **Data classification tagging** — all returned data is tagged with sensitivity level
- **Health checks** — each adapter reports connectivity status
- **Timeout and retry policies** — configurable per adapter (default 10 second timeout, at most 1 retry, no retry on 4xx)
- **Graceful degradation** — on failure, the system routes to "contact staff" rather than erroring

### Supported Protocols

| Protocol | Adapter Type |
|----------|-------------|
| REST / JSON | Pass-through |
| SOAP / XML | Translation |
| ODBC / SQL | Direct query |
| File / FTP | Batch ingest |
| Custom / Proprietary | Custom adapter |

Adapters are added one at a time and validated independently before the next is integrated.

### Session-Scoped Caching

Data fetched from legacy systems is cached only for the duration of the session and purged on session end. The cache is read-optimized and non-authoritative — the source system remains the system of record.

---

## 7. Authentication and Identity

### Staff Authentication

- NextAuth with credential-based login (username + verification code)
- Session tokens stored server-side
- Supports plugging in SAML or OIDC for municipal SSO
- Role-based access controls: `department_staff`, `supervisor`, `department_head`, `records_officer`, `finance_staff`, `city_attorney_office`, `data_steward`, `it_director`

### Resident Identity

Three tiers with graceful upgrade:

- **Anonymous** — no identity required, suitable for FAQ and policy lookups
- **Verified** — light verification (email), required for intake submissions
- **Authenticated** — full identity verification, required for payments and case history

The system prompts residents to upgrade their session tier only when a specific action requires it.

---

## 8. Deployment and Operations

### Container Setup

Docker Compose orchestrates the data layer services:

```bash
# Start PostgreSQL 17, ChromaDB, and Ollama
docker compose up -d

# Or use the setup script (also pulls the LLM model)
bash scripts/setup_infra.sh
```

### Database Migrations

```bash
alembic upgrade head
```

### Backend

```bash
pip install -e ".[postgres,dev]"
uvicorn municipal.web.app:create_app --factory --reload --port 8080
```

### Frontend

```bash
pnpm install
pnpm dev      # Development
pnpm build    # Production build
```

### API Client Generation

The TypeScript API client is auto-generated from the FastAPI OpenAPI schema:

```bash
bash scripts/generate-openapi.sh
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://municipal:municipal_dev@localhost:5432/municipal` | PostgreSQL connection |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8080` | Backend API URL for frontend |
| `MUNICIPAL_LLM_MODEL` | `llama3.1:8b` | LLM model identifier |
| `NEXTAUTH_SECRET` | *(must be set)* | NextAuth session encryption key |
| `NEXTAUTH_URL` | *(must be set)* | Staff portal canonical URL |

---

## 9. Monitoring and Observability

### Structured Logging

The backend uses `structlog` for structured JSON logging. All log entries include session ID, request ID, and timestamp.

### Mission Control Metrics

The staff dashboard provides real-time visibility into:

- Active session count and status
- Pending approval queue depth
- Response latency distribution
- Session volume over time

### Health Checks

All Docker services include health check endpoints:

- PostgreSQL: `pg_isready`
- ChromaDB: HTTP health endpoint on port 8000
- Ollama: HTTP health endpoint on port 11434

### Testing

```bash
# Full test suite (560+ tests)
python3 -m pytest tests/ -x -q

# With coverage reporting
python3 -m pytest tests/ --cov=municipal --cov-report=term-missing
```

---

## 10. Disaster Recovery and Data Retention

### Backup Targets

| Data Store | Backup Method | Priority |
|-----------|--------------|----------|
| PostgreSQL | Standard pg_dump / streaming replication | Critical |
| ChromaDB | Volume snapshot (can be rebuilt from source documents) | High |
| Audit logs | Append-only store with secondary backup location | Critical |
| YAML configuration | Version-controlled in repository | Standard |
| LLM model weights | Re-downloadable from model registry | Low |

### Data Retention

Audit logs and case records are retained according to your municipal records retention schedule. The append-only audit store prevents modification or deletion of historical entries. Retention periods should be configured per your jurisdiction's requirements.

### Recovery Procedure

1. Restore PostgreSQL from backup
2. Restore ChromaDB volume (or re-ingest source documents)
3. Start Docker services via `docker compose up -d`
4. Run `alembic upgrade head` to ensure schema is current
5. Start backend and frontend services
6. Verify health check endpoints

---

## Summary

| Concern | Approach |
|---------|----------|
| Data sovereignty | All processing on municipal infrastructure; air-gap supported |
| LLM hosting | Self-hosted Ollama or vLLM; no external API dependency |
| Sensitive calculations | Deterministic code engines, never LLM |
| Access control | Role-based auth, tiered resident identity, approval gates |
| Audit | Append-only, SHA-256 hashed, comprehensive logging |
| Legacy integration | Adapter pattern with per-system health checks and fallback |
| Configuration | YAML-driven business rules, modifiable without code changes |
| Testing | 560+ automated tests, model evaluation harness |
| Compliance | WCAG 2.1 AA, data classification, records retention support |
