# Evaluation

Current state of quality assurance and evaluation for the Loan Agent MVP.

## Current State

- **Automated tests**: None. No pytest, unittest, or vitest in the codebase.
- **Seed data**: Used for manual validation. `seed_test_cases.sql` adds Alice Minimal, Bob Collateral, Carol Decline alongside init.sql’s 10 applicants.
- **Verification**: Manual runs via UI and API (curl/Postman).

## Suggested Test Strategy

### Unit Tests

| Target | Scope |
|--------|-------|
| `merge_underwriting_signals` (policy.py) | All risk combos: low/medium/high credit, cashflow, collateral; tool_failed; missing_data |
| Tool functions | Mock DB; assert output shape and key fields for known inputs |
| `resolve_applicants_by_name` | Empty, single, multiple matches |
| `AgentContext` helpers | entities, applicant_id, loan_id, months properties |

### API Tests

| Target | Scope |
|--------|-------|
| Health | GET /health → 200, status ok |
| Data | GET /data/applicants → 200, valid ApplicantSummary[] |
| Tools | POST each tool with valid/invalid payloads; assert 200 or 400 |
| Agent run | Deterministic: with applicant_id; autonomous: with/without applicant_id |
| Agent continue | Valid session + reply; expired session |
| Agent chat | New session; continue session; missing applicant_id |

Use FastAPI `TestClient`; seed DB (or use in-memory) for deterministic results.

### Integration / E2E

| Flow | Steps |
|------|-------|
| Deterministic full run | Select applicant → Analyze → verify Overview content |
| Autonomous + clarification | Run without applicant → reply with name → verify result |
| Chat | Send question → verify answer; send follow-up → verify context |

E2E can use Playwright/Cypress against the UI, or API-only against a running stack.

## LLM Output Evaluation

Agent uses OpenAI for:
- Intent extraction
- Planning (tool horizon)
- Router (next tool choice)
- Reasoning (goal_met, confidence)
- Decision explanation
- Outcome analysis (customer_information_used, analysis_findings, final_verdict)
- Chat answers

**Evaluation criteria** (for future work):
- Explanation stays within tool outputs (no invented numbers)
- Outcome analysis keys populated when data exists
- Chat answers grounded in provided context
- No hallucination of applicant/loan data

**Current**: No automated LLM output evaluation. Manual review of sample runs is the only check.

## Regression Triggers

- Policy threshold changes
- Tool input/output schema changes
- New tools or tool reordering
- Clarification or chat flow changes

## Tool Coverage

| Tool | Testable without LLM |
|------|----------------------|
| calculate_credit_risk | Yes (deterministic) |
| analyze_cashflow | Yes (deterministic) |
| list_applicant_loans | Yes (deterministic) |
| assess_collateral | Yes (deterministic) |

All four tools are deterministic; unit tests can mock `get_conn` and assert on outputs.
