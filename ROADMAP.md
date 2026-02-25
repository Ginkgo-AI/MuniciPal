# ROADMAP.md — Munici-Pal

**Munici-Pal** is a secure, sovereign AI orchestration layer designed specifically for municipal government.
It bridges the gap between complex regulations, legacy systems, and resident needs while ensuring staff retain final authority over all legal, regulatory, and financial actions.

This roadmap defines a realistic, compliance-first path from concept → production deployment.

---

# 0) Product Vision

Munici-Pal acts as a **trusted digital civic assistant** that:

- Helps residents navigate city services
- Accelerates structured workflows (permits, FOIA, 311)
- Reduces staff administrative burden
- Preserves legal defensibility
- Operates entirely within municipal data sovereignty boundaries

---

# 1) Foundational Principles ("City Charter")

## 1.1 Trust & Safety (Non-Negotiables)

**Human-in-the-Loop (HITL)**
AI proposes; Staff disposes.
No authoritative database writes without explicit staff approval.

**Data Sovereignty**
All sensitive data remains within:

- On-prem municipal infrastructure OR
- Approved Government Cloud (FedRAMP High / StateRAMP)

**Deterministic Logic for Sensitive Decisions**

| Handled by Code/Services | Handled by LLM |
|---------------------------|-----------------|
| Fee calculations | Language generation |
| Setbacks | Reasoning assistance |
| Deadlines | Guidance |
| Compliance math | Summarization |

**Auditability**

Every interaction tied to:

- Session ID
- Prompt version
- Tool calls
- Data sources
- Approval chain (if applicable)

---

## 1.2 Equity & Public Access ("Public Good")

**Accessibility First**

- WCAG 2.1 AA minimum
- Screen reader compatibility
- Keyboard navigation
- Color contrast compliance

**Multilingual Support**

- Native support for top local languages
- Translation + culturally neutral phrasing

**Low-Bandwidth Optimization**

- Mobile-first UX
- Minimal heavy UI dependencies

---

## 1.3 Resident Identity & Authentication

**Session Types**

| Type | Capabilities | Use Cases |
|------|-------------|-----------|
| Anonymous | Knowledge queries, general info | FAQ, policy lookups |
| Verified (light) | Intake submissions, case tracking | Permit applications, 311 |
| Authenticated (full) | FOIA requester tracking, payment, case history | FOIA, permits, finance |

**Requirements**

- Support municipal SSO where available
- Integration with existing resident portals
- Session continuity across channels (web, phone, kiosk)
- Clear consent and data handling disclosure per session type
- Graceful upgrade from anonymous → verified when needed

---

# 2) Deployment & Infrastructure Strategy

## 2.1 Self-Hosted LLM ("Local Brain")

Munici-Pal must support **municipality-controlled model hosting**.

### Supported Modes

- Fully offline / air-gapped
- On-prem GPU servers
- Hybrid (local primary + policy-approved fallback)

### Potential Runtimes

- Ollama
- vLLM
- OpenAI-compatible local endpoints
- Anthropic-compatible local endpoints

### Candidate Models

- Llama 3 / Llama family
- Mistral / Mixtral
- Domain-fine-tuned civic models (future)

### Model Evaluation Framework

Before committing to a model + runtime, evaluate candidates against:

| Criterion | Method |
|-----------|--------|
| Regulatory language accuracy | Golden dataset of municipal code Q&A pairs |
| Hallucination rate | Adversarial probes with known-false premises |
| Citation fidelity | Verify source attribution against ground truth |
| Multilingual quality | Native speaker review of top local languages |
| Latency / throughput | Load testing under expected concurrent sessions |
| Resource footprint | GPU/RAM requirements vs. available infrastructure |

Maintain a **civic eval harness** that can be re-run on model upgrades.

---

## 2.2 Cloud Fallback (Optional / Policy-Controlled)

Allowed only when:

- Explicitly approved
- Encrypted tunnel
- No persistent storage of resident data

Example:

- Azure OpenAI (Government Tier)

---

## 2.3 Data Residency ("Municipal Boundary")

Applies to:

- Conversations
- Attachments
- Case memory
- Embeddings / vector DB
- Graph DB
- Audit logs

**Default Policy:** No external transmission

---

# 3) Legacy Bridge ("Reality Layer")

Municipal systems are often:

- Legacy SQL
- SOAP/XML
- Vendor-locked APIs
- Non-modern schemas

### Strategy: Adapter Pattern

```
Legacy System → Bridge Adapter → Clean JSON → Agent Runtime
```

### Responsibilities

- Protocol translation (SOAP/XML → JSON)
- Schema normalization
- Data classification tagging
- Real-time fetch only
- Zero-persistence cache (purged after session)

### Integration Risk Mitigation

Legacy integrations carry the highest execution risk. Mitigate with:

- **Vendor liaison early** — engage system vendors in Phase 0 to assess API availability and cooperation
- **Schema discovery sprints** — dedicated time to document actual (not assumed) system behavior
- **Adapter test harnesses** — mock endpoints for each legacy system to enable development without live access
- **Incremental rollout** — one system at a time, validated before moving to the next
- **Fallback to manual** — every adapter must degrade gracefully to "contact staff" if the connection fails

---

# 4) Core Functional Domains

| Domain | Purpose |
|--------|---------|
| Knowledge & Policy | Ordinances, fees, SOPs |
| Permitting | Intake, validation, status |
| FOIA / Records | Intake, retrieval assist |
| 311 / Requests | Ticket creation, routing |
| Inspections | Scheduling, reminders |
| Finance | Deterministic fee/tax engine |
| Governance | Logs, approvals, policy |

---

# 5) System Architecture (End State)

## 5.1 Control Plane ("Mission Control")

Features:

- Live session monitoring
- Session shadowing / takeover
- Tool call inspection
- Approval queue
- Prompt/policy management
- Audit log viewer
- Metrics dashboard
- Incident/security review

---

## 5.2 Agent Runtime ("Orchestrator")

Components:

- Channel router
- Intent detection
- Policy guardrails
- Planner
- Tool selector
- Tool executor (sandboxed)
- Memory manager
- Citation engine
- Response composer

---

## 5.3 Tool Registry

Each tool defined by:

- JSON schema
- Role/permission requirements
- Sensitivity classification
- Approval requirement
- Logging policy
- Rate limits
- Idempotency keys
- Dry-run capability

---

## 5.4 Data Layer

### Knowledge Base (RAG)

Sources:

- Municipal code
- FAQs
- Fee schedules
- Policies/SOPs

Features:

- Citations
- Version tracking
- Confidence scoring

---

### Case Memory

Per-case timeline:

- Messages
- Tool calls
- Documents
- Decisions
- Approvals

---

### Connector Cache

- Read-optimized
- Non-authoritative
- Policy-controlled

---

### Graph Layer

> **Note:** The graph layer is a planned deliverable (Phase 2), not optional. The entity relationships it models are central to permitting, 311, and inspection workflows.

Relationships:

- Parcels ↔ Owners
- Permits ↔ Inspections
- Contractors ↔ Licenses
- Cases ↔ Documents
- Residents ↔ Cases ↔ Departments

---

# 6) Governance & Guardrails

## 6.1 Approval Gates

Always required for:

- Permit issuance/denial
- FOIA release
- Payments/refunds
- Legal correspondence
- Record modification

---

## 6.2 Prompt Injection Defense

- Treat attachments & external content as **UNTRUSTED**
- Block tool execution from untrusted instructions
- Require justification + policy checks

---

## 6.3 Hallucination Kill-Switch

If retrieval confidence low:

> "I cannot find the specific policy. Let me connect you with a staff member."

---

## 6.4 Immutable Audit Logs

Log:

- Tool calls
- Prompts
- Outputs
- Actor/session
- Approval chain

Stored:

- Append-only
- Hashed
- Secondary secure location

---

## 6.5 Deterministic Engines

Separate services for:

- Fees
- Taxes
- Deadlines
- Compliance math

---

# 7) Testing & Validation Strategy

## 7.1 RAG Accuracy

- **Golden dataset** per department: curated Q&A pairs with expected answers and source citations
- Run on every model upgrade, prompt change, or knowledge base update
- Track accuracy, citation correctness, and hallucination rate over time

## 7.2 Regression Testing

- Automated test suite for deterministic engines (fees, deadlines, compliance)
- Integration tests for each legacy bridge adapter
- End-to-end scenario tests for each workflow (permit intake, FOIA, 311)

## 7.3 Policy Change Validation

- When ordinances or policies are updated in the knowledge base, automatically re-run affected golden dataset entries
- Flag any answer drift for staff review before the update goes live

## 7.4 Model Upgrade Protocol

1. Run full civic eval harness against candidate model
2. Compare results to current model baseline
3. Shadow mode deployment (new model runs in parallel, outputs logged but not served)
4. Staff review of divergent answers
5. Promote only after passing all thresholds

## 7.5 Security Testing

- Prompt injection test suite (updated quarterly)
- Penetration testing on control plane and public-facing channels
- Data residency verification (confirm no external transmission)

---

# 8) Staff Onboarding & Change Management

## 8.1 Principles

- Staff are partners, not passengers — involve them from Phase 0
- Training is continuous, not a one-time event
- Feedback loops must be fast and visible

## 8.2 Per-Phase Onboarding

| Phase | Staff Activities |
|-------|-----------------|
| Phase 0 | Department champion selection, system inventory workshops, expectation setting |
| Phase 1 | Shadow mode observation, accuracy feedback, FAQ gap identification |
| Phase 2 | Intake workflow co-design, validation rule review, multilingual review |
| Phase 3 | Integration acceptance testing, escalation path training, Mission Control training |
| Phase 4 | Advanced feature training, report customization, continuous improvement rituals |

## 8.3 Feedback Mechanisms

- In-app "flag this answer" button for staff
- Weekly digest of flagged answers → knowledge base corrections
- Monthly retrospective with pilot department leads
- Quarterly satisfaction survey (staff + residents)

## 8.4 Gradual Rollout Strategy

Within each phase:

1. **Internal only** — staff-facing, no resident access
2. **Shadow mode** — runs alongside existing process, outputs compared but not authoritative
3. **Assisted mode** — resident-facing with staff monitoring every session
4. **Supervised mode** — resident-facing with staff spot-checking
5. **Production mode** — normal operation with audit and escalation paths

---

# 9) Development Phases

---

## **Phase 0 — Foundation (Weeks 1-4)**

**Focus:** Infrastructure, evaluation, and stakeholder alignment

### Deliverables

- Self-hosted LLM runtime stood up and validated
- Vector DB deployed and configured
- CI/CD pipeline for model and knowledge base deployments
- Model evaluation harness built and initial candidate evaluated
- Resident authentication strategy defined
- System/API inventory completed for pilot departments
- Data classification rules defined
- Approval policies documented
- Staff champions identified and onboarded
- Baseline metrics established

### Success Criteria

- LLM responds to queries locally with acceptable latency
- Eval harness produces repeatable scores
- Pilot departments committed with clear expectations

---

## **Phase 1 — Digital Librarian (Weeks 5-12)**

**Focus:** Read-only trust building

### Deliverables

- Knowledge Base RAG pipeline
- Ordinance/FAQ ingestion pipeline
- Citation engine with confidence scoring
- Web chat UI (ADA compliant)
- Staff Mission Control v0 (session viewer, audit log)
- Audit logging foundation
- Golden dataset v1 for pilot departments
- Staff shadow mode and feedback workflow

### Success Criteria

- Accurate cited answers (measured against golden dataset)
- High resident satisfaction (CSAT baseline established)
- Staff confidence established through shadow mode

---

## **Phase 2 — Intake Assistant (Weeks 13-22)**

**Focus:** Structured data collection + entity relationships

### Deliverables

- Permit intake wizard
- FOIA intake wizard
- Validation flows
- GIS / parcel lookup integration
- Graph layer (parcels, owners, permits, contractors)
- Resident identity: anonymous → verified upgrade flow
- Multilingual support (initial languages)
- Case packet export (PDF/JSON)

### Success Criteria

- Reduced incomplete submissions
- Fewer staff follow-ups
- Graph queries support cross-entity lookups

---

## **Phase 3 — Integrated Clerk (Weeks 23-36)**

**Focus:** System connectivity (expanded timeline for integration risk)

### Deliverables

- Legacy Bridge adapters (one system at a time, incremental)
- Read-only permit status lookup
- 311 ticket reads/writes (low risk)
- Notification engine (SMS/email)
- Case memory linking
- Mission Control v1
- Full resident authentication integration

### Success Criteria

- Reliable status answers from live systems
- Stable integrations with graceful fallback
- Each adapter passes its test harness before the next begins

---

## **Phase 4 — Reviewer (Weeks 37+)**

**Focus:** Staff efficiency & compliance assist

### Deliverables

- Redaction suggestions (FOIA)
- Document inconsistency detection
- Cross-field validation
- Advanced summaries/reports
- Annual "Sunshine Report" generation

### Success Criteria

- Measurable staff time savings
- Compliance maintained
- Positive staff satisfaction trend

---

# 10) Success Metrics

## Resident Outcomes

- Deflection rate
- Intake completion rate
- Time-to-submission
- Satisfaction (CSAT)

---

## Staff Outcomes

- Cycle time reduction
- Contacts per case
- Error reduction
- Approval throughput

---

## Compliance & Risk

- Unauthorized writes: **0**
- Audit completeness: **100%**
- PII incidents: **0**
- Hallucination rate: **tracked, trending down**

---

# 11) Procurement Strategy

Munici-Pal:

- Vendor-neutral orchestration layer
- Does NOT replace systems of record
- Augments existing investments
- Compatible with major municipal platforms

---

# 12) Munici-Pal is NOT

- A replacement for staff
- A legal authority
- A system of record
- An autonomous decision maker

---

# 13) Immediate Next Steps

- [ ] Select pilot departments
- [ ] Identify department champions
- [ ] Inventory systems/APIs (Phase 0 deliverable)
- [ ] Define data classification rules
- [ ] Define approval policies
- [ ] Procure / allocate GPU infrastructure
- [ ] Stand up self-hosted LLM
- [ ] Build and run model evaluation harness
- [ ] Define resident authentication strategy
- [ ] Build Phase 0 infrastructure
- [ ] Establish baseline metrics
- [ ] Begin Phase 1 prototype

---

**Owner:**
**Last Updated:** 2026-02-25
**Version:** 2.0
