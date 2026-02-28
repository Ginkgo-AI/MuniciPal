# REFERENCE.md — MuniciPal Technical Reference

This document serves as a quick-reference companion to [ROADMAP.md](./ROADMAP.md).
It defines key terms, architectural components, compliance requirements, and decision records in a format optimized for implementers.

---

## Table of Contents

1. [Glossary](#1-glossary)
2. [Architecture Component Reference](#2-architecture-component-reference)
3. [Data Classification](#3-data-classification)
4. [Compliance & Regulatory Reference](#4-compliance--regulatory-reference)
5. [Integration Patterns](#5-integration-patterns)
6. [Tool Registry Schema](#6-tool-registry-schema)
7. [Approval Gate Definitions](#7-approval-gate-definitions)
8. [Evaluation Harness Specification](#8-evaluation-harness-specification)
9. [Rollout Stage Definitions](#9-rollout-stage-definitions)
10. [Decision Log](#10-decision-log)

---

## 1) Glossary

| Term | Definition |
|------|-----------|
| **HITL** | Human-in-the-Loop. Staff must approve all authoritative writes. |
| **RAG** | Retrieval-Augmented Generation. LLM answers grounded in retrieved source documents. |
| **Golden Dataset** | Curated set of question-answer-source triples used to evaluate RAG accuracy. |
| **Civic Eval Harness** | Automated test suite that scores model candidates on municipal-specific criteria. |
| **Mission Control** | Staff-facing control plane for monitoring, approvals, and administration. |
| **Legacy Bridge** | Adapter layer that translates between legacy municipal systems and the agent runtime. |
| **Shadow Mode** | System runs in parallel with existing processes; outputs are logged but not served to residents. |
| **Deterministic Engine** | Code-based service that computes fees, taxes, deadlines, and compliance math — never delegated to an LLM. |
| **Case Memory** | Per-case timeline of all interactions, tool calls, documents, decisions, and approvals. |
| **Graph Layer** | Entity-relationship store modeling parcels, owners, permits, inspections, contractors, licenses, and cases. |
| **Connector Cache** | Read-optimized, non-authoritative, session-scoped cache of data fetched from legacy systems. |
| **Approval Gate** | A policy-enforced checkpoint requiring explicit staff authorization before an action proceeds. |
| **FedRAMP High** | Federal Risk and Authorization Management Program — High impact level. Required for sensitive government cloud workloads. |
| **StateRAMP** | State-level equivalent of FedRAMP for state and local government cloud authorization. |
| **WCAG 2.1 AA** | Web Content Accessibility Guidelines level AA — the accessibility compliance target. |
| **FOIA** | Freedom of Information Act. Public records request process. |
| **311** | Non-emergency municipal service request system. |
| **GIS** | Geographic Information System. Used for parcel lookups, zoning, and spatial queries. |
| **PII** | Personally Identifiable Information. Subject to data residency and handling policies. |

---

## 2) Architecture Component Reference

### 2.1 Control Plane (Mission Control)

| Component | Description | Phase |
|-----------|-------------|-------|
| Session Viewer | Real-time view of active resident/staff sessions | 1 |
| Session Shadowing | Staff can observe and take over live sessions | 3 |
| Audit Log Viewer | Searchable, filterable view of all logged events | 1 |
| Approval Queue | Staff interface for pending approval gates | 3 |
| Prompt Manager | Version-controlled prompt and policy editor | 1 |
| Metrics Dashboard | Operational and outcome metrics display | 3 |
| Incident Review | Security and compliance incident investigation tool | 4 |

### 2.2 Agent Runtime (Orchestrator)

| Component | Description | Phase |
|-----------|-------------|-------|
| Channel Router | Directs incoming messages from web, SMS, kiosk, etc. | 1 |
| Intent Detector | Classifies resident intent to select workflow | 1 |
| Policy Guardrails | Enforces data classification, approval gates, and safety rules | 1 |
| Planner | Decomposes complex requests into tool call sequences | 2 |
| Tool Selector | Chooses appropriate tools based on intent and policy | 2 |
| Tool Executor | Sandboxed execution environment for tool calls | 2 |
| Memory Manager | Reads/writes case memory, manages session context | 2 |
| Citation Engine | Attaches source references to generated responses | 1 |
| Response Composer | Assembles final response with citations, confidence, and formatting | 1 |

### 2.3 Data Layer

| Store | Type | Purpose | Phase |
|-------|------|---------|-------|
| Vector DB | Embeddings | RAG retrieval over knowledge base | 0-1 |
| Graph DB | Entity-relationship | Parcel/owner/permit/case relationships | 2 |
| Case Store | Document/timeline | Per-case interaction history | 2 |
| Connector Cache | Key-value / read-optimized | Session-scoped legacy system data | 3 |
| Audit Store | Append-only log | Immutable event log | 1 |
| Prompt Store | Versioned config | Prompt templates and policy rules | 1 |

---

## 3) Data Classification

All data handled by MuniciPal must be classified. Classification drives residency rules, caching policy, logging behavior, and access controls.

| Level | Label | Examples | Residency | Cache | Logging |
|-------|-------|----------|-----------|-------|---------|
| 1 | **Public** | Published ordinances, fee schedules, FAQs | Any | Allowed | Standard |
| 2 | **Internal** | Staff SOPs, internal notes, draft policies | Municipal boundary | Session-only | Standard |
| 3 | **Sensitive** | Resident PII, case details, permit applications | Municipal boundary | Session-only, encrypted | Enhanced (redacted in logs) |
| 4 | **Restricted** | Legal correspondence, FOIA exemptions, financial records | Municipal boundary, access-controlled | No cache | Full audit, access-logged |

### Classification Rules

- Default to the **highest applicable level** when uncertain
- Attachments from residents are **Sensitive** until reviewed
- External content (web scrapes, third-party data) is **untrusted** and classified **Internal** minimum
- Classification is tagged at ingestion and propagated through the pipeline

---

## 4) Compliance & Regulatory Reference

| Requirement | Standard | Applies To | Notes |
|-------------|----------|-----------|-------|
| Accessibility | WCAG 2.1 AA | All resident-facing UI | Keyboard nav, screen reader, color contrast |
| Data residency | FedRAMP High / StateRAMP | All sensitive data | If cloud is used at all |
| Public records | State FOIA / public records law | Case memory, audit logs | Logs may be subject to records requests |
| Privacy | State/local privacy regulations | PII handling | Consent disclosure required |
| Financial | Municipal finance regulations | Fee/tax calculations | Deterministic engines only |
| Retention | Municipal records retention schedule | Audit logs, case memory | Retention periods vary by record type |
| ADA | Americans with Disabilities Act | All public-facing services | Extends beyond WCAG to service access |

---

## 5) Integration Patterns

### 5.1 Legacy Bridge Adapter Interface

Each adapter must implement:

```
interface BridgeAdapter {
  // Connection
  healthCheck(): Promise<HealthStatus>
  connect(config: AdapterConfig): Promise<Connection>
  disconnect(): Promise<void>

  // Operations
  query(request: NormalizedRequest): Promise<NormalizedResponse>

  // Metadata
  getSchema(): AdapterSchema
  getClassification(): DataClassification
  getSupportedOperations(): Operation[]
}
```

### 5.2 Adapter Requirements

| Requirement | Description |
|-------------|-------------|
| Protocol translation | Convert native protocol (SOAP, XML-RPC, proprietary) → JSON |
| Schema normalization | Map vendor-specific fields to MuniciPal canonical schema |
| Classification tagging | Tag all returned data with appropriate classification level |
| Error handling | Graceful degradation to "contact staff" on failure |
| Timeout policy | Configurable per-adapter; default 10s |
| Retry policy | At most 1 retry; no retry on 4xx |
| Cache policy | Session-scoped, purged on session end |
| Test harness | Mock endpoint that simulates the real system for development/testing |
| Logging | All calls logged with timing, status, and classification |

### 5.3 Supported Source Protocols

| Protocol | Adapter Type | Common In |
|----------|-------------|-----------|
| REST/JSON | Pass-through | Modern vendor APIs |
| SOAP/XML | Translation | Older ERP, permitting systems |
| ODBC/SQL | Direct query | Legacy databases |
| File/FTP | Batch ingest | Report exports, data dumps |
| Custom/Proprietary | Custom adapter | Vendor-specific integrations |

---

## 6) Tool Registry Schema

Every tool registered in the agent runtime must conform to:

```json
{
  "id": "string (unique)",
  "name": "string (human-readable)",
  "description": "string",
  "version": "semver",
  "schema": {
    "input": "JSON Schema",
    "output": "JSON Schema"
  },
  "permissions": {
    "roles": ["string"],
    "classification_max": "Public | Internal | Sensitive | Restricted"
  },
  "policy": {
    "approval_required": "boolean",
    "approval_roles": ["string"],
    "dry_run_supported": "boolean",
    "idempotent": "boolean",
    "rate_limit": "number (calls/minute)",
    "timeout_ms": "number"
  },
  "logging": {
    "log_input": "boolean",
    "log_output": "boolean",
    "redact_fields": ["string"]
  }
}
```

---

## 7) Approval Gate Definitions

| Gate | Trigger | Required Approvers | Timeout | Escalation |
|------|---------|-------------------|---------|------------|
| Permit Decision | Issuance or denial of any permit | Department reviewer + supervisor | 48h | Department head |
| FOIA Release | Release of responsive records | Records officer | 5 business days | City clerk |
| Payment/Refund | Any financial transaction | Finance staff | 24h | Finance director |
| Legal Correspondence | Outbound legal communication | City attorney's office | 24h | City attorney |
| Record Modification | Any write to system of record | Department staff + supervisor | 24h | Department head |
| Data Export | Bulk data export or report generation | Data steward | 24h | IT director |

---

## 8) Evaluation Harness Specification

### 8.1 Golden Dataset Format

Each entry:

```json
{
  "id": "string",
  "department": "string",
  "category": "string (ordinance | fee | process | policy)",
  "question": "string",
  "expected_answer": "string",
  "expected_sources": ["string (document IDs)"],
  "difficulty": "easy | medium | hard",
  "last_verified": "ISO 8601 date"
}
```

### 8.2 Evaluation Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Answer accuracy | Semantic match to expected answer | > 90% |
| Citation precision | % of cited sources that are relevant | > 95% |
| Citation recall | % of expected sources that are cited | > 85% |
| Hallucination rate | % of answers containing unsupported claims | < 5% |
| Refusal rate | % of questions correctly refused (no source) | > 90% |
| Latency (p50) | Median response time | < 3s |
| Latency (p95) | 95th percentile response time | < 8s |

### 8.3 When to Run

- On every model candidate evaluation
- On every prompt template change
- On every knowledge base update (affected entries only)
- Weekly full regression (automated)

---

## 9) Rollout Stage Definitions

Each phase progresses through these stages before advancing:

| Stage | Audience | Staff Role | Resident Access | Duration |
|-------|----------|-----------|----------------|----------|
| **Internal** | Staff only | Direct users | None | 1-2 weeks |
| **Shadow** | Staff only | Compare outputs to existing process | None | 2-4 weeks |
| **Assisted** | Staff + residents | Monitor every session | Full, with staff backup | 2-4 weeks |
| **Supervised** | Staff + residents | Spot-check sessions | Full | 2-4 weeks |
| **Production** | All | Normal audit and escalation | Full | Ongoing |

### Promotion Criteria

To advance from one stage to the next:

- Golden dataset metrics meet targets
- No unresolved critical incidents
- Staff satisfaction survey above threshold
- Department champion sign-off

---

## 10) Decision Log

Record significant architectural and policy decisions here as they are made.

| # | Date | Decision | Rationale | Status |
|---|------|----------|-----------|--------|
| 1 | 2026-02-25 | Graph layer is a planned Phase 2 deliverable, not optional | Entity relationships are central to permitting and 311 workflows; deferring creates integration debt | Accepted |
| 2 | 2026-02-25 | Add Phase 0 for infrastructure before feature work | LLM hosting, vector DB, CI/CD, and eval harness must exist before Phase 1 can begin | Accepted |
| 3 | 2026-02-25 | Expand Phase 3 timeline (13 weeks vs. original 10) | Legacy integration is the highest-risk area; incremental adapter rollout requires more time | Accepted |
| 4 | 2026-02-25 | Resident authentication defined as three tiers (anonymous, verified, authenticated) | Different workflows require different identity assurance levels; forcing full auth would reduce accessibility | Accepted |
| 5 | 2026-02-25 | Model upgrades require shadow mode comparison before promotion | Prevents regression in answer quality when swapping or updating models | Accepted |

---

**Owner:**
**Last Updated:** 2026-02-25
**Version:** 1.0
