# Munici-Pal — Features Overview

**Your municipality's AI-powered civic services platform.**

Munici-Pal is a secure, sovereign AI assistant that helps residents navigate city services while giving staff the tools to work faster — without giving up control. It sits alongside your existing systems, not on top of them.

---

## For Residents

### Conversational Service Assistant

Residents interact with a friendly chat interface to get answers about city services, policies, fees, and procedures. Every answer is grounded in your municipality's actual documents — ordinances, fee schedules, SOPs — and includes citations so residents can verify the source.

When the system isn't confident in an answer, it says so and connects the resident with a staff member rather than guessing.

### Guided Intake Wizards

Instead of navigating confusing PDF forms, residents are walked through structured, step-by-step applications for:

- **Building permits** — property details, project scope, contractor info, document uploads
- **FOIA / public records requests** — guided request submission with automatic fee estimation
- **311 service requests** — categorized ticket creation with location and description

Each wizard validates inputs in real time, calculates applicable fees upfront, and produces a complete application packet — reducing incomplete submissions and back-and-forth with staff.

### Transparent Fee Calculations

All fees are computed deterministically from your published fee schedules. Residents see exactly what they owe and why, broken down by line item. No surprises, no black boxes.

### Multilingual Support

The platform supports multiple languages out of the box, so non-English-speaking residents can access the same services and information.

### Email Notifications

Residents receive automatic updates as their cases move through the process — submission confirmations, status changes, approvals, and denials.

---

## For Staff

### Mission Control Dashboard

A real-time operational command center where staff can:

- **Monitor active sessions** — see what residents are asking right now
- **Review approval queues** — permits, FOIA releases, payments, and data exports all route through configurable approval gates before any action is taken
- **Browse audit logs** — every interaction is logged with session ID, timestamps, data sources cited, and the full approval chain
- **Track operational metrics** — active sessions, response quality, and throughput at a glance

### Human-in-the-Loop Governance

Munici-Pal never makes authoritative decisions on its own. Six approval gates ensure staff sign off on:

| Action | Who Approves | Escalation |
|--------|-------------|------------|
| Permit issuance or denial | Department reviewer + supervisor | Department head |
| FOIA record release | Records officer | City clerk |
| Payments and refunds | Finance staff | Finance director |
| Legal correspondence | City attorney's office | City attorney |
| Record modifications | Department staff + supervisor | Department head |
| Bulk data exports | Data steward | IT director |

Every gate has configurable timeouts and automatic escalation so nothing falls through the cracks.

### FOIA Review Assistance

When preparing FOIA responses, the system suggests redactions for sensitive information — Social Security numbers, phone numbers, email addresses — with confidence ratings. Staff review and approve every suggestion; nothing is redacted automatically.

### Cross-Field Validation and Inconsistency Detection

Submitted applications are automatically checked for internal inconsistencies and missing information before they reach a reviewer's desk, reducing the time staff spend on obvious errors.

### Document Summaries and Reports

Staff can generate summaries of submitted applications and produce structured reports. The annual **Sunshine Report** — a transparency report on FOIA activity — can be generated as a formatted PDF.

### Case Packet Export

Complete application packets can be exported as PDF or JSON for archival, inter-departmental sharing, or integration with existing document management systems.

---

## For IT and Administration

### Data Sovereignty

All data — conversations, documents, embeddings, audit logs — stays within your municipal infrastructure. The platform supports fully offline and air-gapped deployments. No resident data is transmitted to external services.

### Self-Hosted AI

The AI model runs on your own hardware using open-source runtimes (Ollama or vLLM). Default model is Llama 3.1, but any compatible model can be swapped in. A built-in evaluation harness lets you test model candidates against your own municipal Q&A datasets before deploying them.

### Configuration, Not Code

Core business logic is driven by YAML configuration files that non-developers can review and modify:

- **Fee schedules** — add or adjust fees without touching code
- **Deadline rules** — define permit and application timelines
- **Approval policies** — configure who approves what, timeouts, and escalation paths
- **Intake wizards** — define application steps, fields, and validation rules
- **Notification templates** — customize email content for each case event
- **Redaction rules** — define PII patterns for FOIA review assistance
- **Data classification** — set sensitivity levels that drive access controls and logging

### Legacy System Integration

Munici-Pal connects to your existing systems through a bridge adapter layer. Whether your systems speak REST, SOAP/XML, ODBC, or something proprietary, the adapter pattern translates them into a clean internal format. Each adapter includes health checks, timeout policies, and graceful fallback — if a connection fails, the system routes to staff rather than erroring out.

### Immutable Audit Trail

Every action is logged to an append-only, integrity-hashed audit store. Logs include session IDs, tool calls, data sources, timestamps, and the full approval chain. These logs are themselves subject to your records retention policies and are available for compliance review or public records requests.

### Data Classification

All data flowing through the system is tagged with a classification level:

| Level | Examples | Handling |
|-------|----------|----------|
| **Public** | Ordinances, fee schedules, FAQs | Standard logging, cacheable |
| **Internal** | Staff SOPs, draft policies | Municipal boundary, session-only cache |
| **Sensitive** | Resident PII, permit applications | Encrypted cache, enhanced logging |
| **Restricted** | Legal correspondence, financial records | No cache, full audit, access-controlled |

Classification drives caching, logging, and access control decisions automatically.

### GIS Integration

Parcel lookups, zoning queries, and spatial data integrate with your existing GIS infrastructure to support address validation and property-based workflows.

### Entity Relationship Graph

An internal knowledge graph connects parcels, owners, permits, inspections, contractors, and licenses — enabling cross-entity lookups that would otherwise require staff to search multiple systems.

---

## Deployment Model

Munici-Pal is designed for progressive rollout:

1. **Internal** — staff-only testing
2. **Shadow** — runs alongside existing processes, outputs compared but not served
3. **Assisted** — resident-facing with staff monitoring every session
4. **Supervised** — resident-facing with staff spot-checking
5. **Production** — normal operation with audit and escalation

Each stage has clear promotion criteria before advancing, so your team stays comfortable at every step.

---

## What Munici-Pal is NOT

- **Not a replacement for staff** — it's a tool that makes staff faster and more effective
- **Not a legal authority** — all authoritative decisions require human approval
- **Not a system of record** — it augments your existing systems, never replaces them
- **Not an autonomous agent** — every consequential action has a human in the loop

---

*For technical deployment details, see the companion IT Technical Reference.*
