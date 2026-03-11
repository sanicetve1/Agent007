# Phases

## Phase 1: MVP (Current)

**Status**: Implemented

- **Data layer**: PostgreSQL with 6 tables (applicants, credit_scores, transactions, loans, collateral, documents). Init schema + 10-applicant seed + 3 test cases (Alice Minimal, Bob Collateral, Carol Decline)
- **Tools**: Four deterministic tools (credit risk, cashflow, list loans, assess collateral) via tool registry
- **Agent modes**: Deterministic pipeline (fixed tool order) and autonomous ReAct (Intent → Planning → Router → Tool → Observation → Reasoning → Decision)
- **Clarification flow**: Missing applicant_id triggers clarification; `/agent/continue` resumes with user reply
- **Customer chat**: Applicant-scoped Q&A via `/agent/chat` (autonomous only)
- **API**: FastAPI with `/health`, `/data/applicants`, `/tools/*`, `/agent/run`, `/agent/continue`, `/agent/chat`
- **UI**: React + Vite; applicant list, loan selection, Analyze, Overview/Sequence/JSON tabs, per-customer chat
- **Deployment**: Docker (API, UI, Postgres), DEPLOY.md for Lightsail and other hosts

**Gaps vs planning**: No governance APIs, no mandatory gate checks, no auth, no automated tests.

---

## Phase 2: Service Layer (Planned)

From `plan.md — Service Layer`:

- **Data services**: `GET /data/applicants/{id}`, `/data/credit-score/{id}`, `/data/transactions/{id}`, `/data/loans/{id}`, `/data/collateral/{loan_id}`, `/data/documents/{id}`
- **Analytics services**: `GET /analytics/exposure/{id}`, `/analytics/income/{id}`, `/analytics/monthly-obligations/{id}`, `/analytics/dti/{id}`
- **Governance services**: `GET /governance/kyc/{id}`, `/governance/required-data/{id}`, `/governance/policy/{id}`

Agent tools would call these services (or a thin wrapper) instead of direct DB access. Enables separation of data/analytics/governance layers.

---

## Phase 3: Autonomy Boundaries (Planned)

From `plan.md Autonomy Boundaries`:

- Implement mandatory gates: `check_kyc`, `check_required_data`, `check_policy`
- Ensure agent cannot bypass gates; server-side verification that gates ran and passed
- Output policy: `recommend_approve` | `recommend_reject` | `recommend_manual_review`
- Audit & trace: correlation_id, tool calls, gate results, version stamps

---

## Phase 4: Data Layer Expansion (Planned)

From `plan.md — Data Layer`:

- Richer seed: 10 applicants with profiles A1–A10 (high income, medium, low, self-employed, no loans, high EMIs, late payments proxy, strong/weak collateral, borderline)
- 12–24 transactions per applicant across ~6 months
- Align document extracted_income with applicant income
- Scripts: `init_db.sh`, `reset_db.sh`

---

## Phase 5: Interpretive & Governance Tools (Future)

- Interpretive tools: PDF extraction, bank-statement summarization, employment classification, inconsistency detection
- Governance tools: AML screening, policy threshold enforcement
- Tool interface per `plan.md Tool Interface Definition`: success/error shapes, correlation id, timeouts, retries
