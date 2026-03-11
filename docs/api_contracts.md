# API Contracts

All endpoints are defined in `loan_agent/api/server.py`.

## Base

- **Health**: `GET /health` → `{ "status": "ok" }`

## Data

### GET /data/applicants

List applicants.

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| limit | int | 20 | Max rows |

**Response**: Array of `ApplicantSummary`

```json
{
  "applicant_id": "uuid",
  "full_name": "string",
  "annual_income": 120000.0,
  "kyc_status": "verified"
}
```

## Tools (Direct Invocation)

### POST /tools/calculate_credit_risk

**Request**: `CreditRiskReq` — `{ "applicant_id": "uuid" }`

### POST /tools/analyze_cashflow

**Request**: `CashflowReq` — `{ "applicant_id": "uuid", "months": 6 }`

### POST /tools/list_applicant_loans

**Request**: `ListLoansReq` — `{ "applicant_id": "uuid", "include_closed": false }`

### POST /tools/assess_collateral

**Request**: `AssessCollateralReq` — `{ "loan_id": "uuid", "threshold_ratio": 1.0 }`

All tool endpoints return the tool’s result dict or `400` with error detail.

## Agent

### POST /agent/run

Run underwriting (deterministic or autonomous depending on `ENABLE_AUTONOMY`).

**Request**: `UnderwritingReq`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| applicant_id | string | deterministic: yes, autonomous: no | — | Applicant UUID |
| loan_id | string | no | — | Loan to assess; optional if single loan |
| months | int | no | 6 | Cashflow analysis window (1–24) |
| model | string | no | "gpt-4.1-mini" | OpenAI model |

**Response**: Underwriting result (see Agent Response Shape) or `status: "clarification_needed"` with `session_id`, `clarification_question`, `clarification_options`.

**Deterministic mode**: `applicant_id` required; returns 400 if missing.

### POST /agent/continue

Continue after clarification (autonomous only).

**Request**: `AgentContinueReq`

| Field | Type | Description |
|-------|------|-------------|
| session_id | string | From clarification response |
| user_reply | string | User answer (UUID or customer name) |
| model | string | Optional, default "gpt-4.1-mini" |

**Response**: Same shape as `/agent/run` or `{ "status": "error", "error": "session_expired", "message": "..." }` if session not found.

**Requires**: `ENABLE_AUTONOMY=true`; otherwise 400.

### POST /agent/chat

Customer-context chat (autonomous only).

**Request**: `AgentChatReq`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| applicant_id | string | yes | Applicant for chat context |
| message | string | yes | User question |
| session_id | string | no | Existing chat session; omit for new |
| model | string | no | Default "gpt-4.1-mini" |

**Response**: `{ "status": "ok", "session_id": "uuid", "answer": "..." }` or error with `status`, `error`, `message`.

**Requires**: `ENABLE_AUTONOMY=true`; otherwise 400.

## Agent Response Shape

Shared by `/agent/run` and `/agent/continue`:

| Field | Type | Description |
|-------|------|-------------|
| applicant_id | string | — |
| credit_risk | object | Tool output |
| cashflow_signal | object | Tool output |
| collateral_status | object | Tool output |
| overall_risk_level | string | low / medium / high |
| recommendation | string | approve / conditional / decline |
| explanation | string | Human-readable summary |
| tool_failed | bool | Any tool failed |
| missing_data | string[] | Missing signals |
| loan_selection_required | bool | Multiple loans, user must pick |
| loan_options | object[] | Available loans |
| selected_loan_id | string? | Chosen loan |
| tool_call_sequence | object[] | Tool invocations |
| llm_outcome_analysis | object | Structured LLM output |
| agent_mode | string | "deterministic" or "autonomous" |
| agent_trace | object[] | Optional trace steps |
| max_steps_reached | bool | Optional; stopped at limit |

## CORS

Allowed origins: `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:5174`, `http://127.0.0.1:5174`. Credentials and all methods/headers allowed.
