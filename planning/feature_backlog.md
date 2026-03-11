# Feature Backlog

Prioritized backlog derived from planning docs and current gaps.

## High Priority

### Governance Tools & Gates
- **check_kyc(applicant_id)**: Return pass/fail from KYC status; agent must not override
- **check_required_data(applicant_id)**: Validate applicant exists, credit score exists, sufficient transactions, income document
- **check_policy(applicant_id, months)**: Hard policy threshold check (score >= 650, DTI <= 0.45, etc.)
- **Mandatory gate enforcement**: Ensure gates run before recommendation; non-bypassable

### Authentication & Security
- API authentication (JWT, mTLS, or API gateway)
- Rate limiting
- CORS configurable for production origins

### Automated Tests
- Unit tests: policy merge, tool output shapes, applicant resolution
- API tests: health, data, tools, agent run/continue/chat
- E2E: deterministic + autonomous flows, clarification, chat

---

## Medium Priority

### Service Layer Refactor
- Split tools to call FastAPI data/analytics/governance endpoints instead of direct DB
- Implement data endpoints: `/data/applicants/{id}`, `/data/credit-score/{id}`, `/data/transactions/{id}`, etc.
- Implement analytics: `/analytics/exposure`, `/analytics/dti`, etc.
- Implement governance: `/governance/kyc`, `/governance/required-data`, `/governance/policy`

### Tool Interface Standardization
- Per `plan.md Tool Interface Definition`: success shape `{ ok, tool, correlation_id, data }`, error shape `{ ok, tool, correlation_id, error }`
- Correlation id propagation (X-Correlation-Id)
- Timeouts (5s data, 10s analytics), retry policy (2 retries for 502/503/504)

### Multi-Loan Clarification
- Support clarification when multiple loans exist and user must select (currently returns early with loan_selection_required)

---

## Lower Priority

### Interpretive Tools
- `extract_income_from_pdf`
- `summarize_bank_statement`
- `classify_employment_type`
- `detect_inconsistencies`

### Observability
- Structured logging (JSON)
- Request/response logging with correlation id
- Metrics (latency, tool call counts)
- Optional: `agent_runs` table for trace persistence

### Richer Seed Data
- 10 applicant profiles per Data Layer plan (A1–A10)
- 12–24 transactions per applicant
- Diverse loan/collateral scenarios

### Output Policy Alignment
- Map current approve/conditional/decline to `recommend_approve` | `recommend_reject` | `recommend_manual_review`
- Add `supporting_evidence`, `assumptions`, `missing_info` to agent output
