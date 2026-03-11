# Data Models

## Database Schema

Defined in `Loan_Agent/DB/init.sql/init.sql`.

### applicants

| Column | Type | Constraints |
|--------|------|-------------|
| applicant_id | UUID | PK, default uuid_generate_v4() |
| full_name | TEXT | NOT NULL |
| dob | DATE | NOT NULL |
| employment_type | TEXT | NOT NULL, CHECK (salaried, self_employed) |
| annual_income | NUMERIC | NOT NULL |
| kyc_status | TEXT | NOT NULL, CHECK (verified, pending) |
| created_at | TIMESTAMP | NOT NULL, default NOW() |
| updated_at | TIMESTAMP | NOT NULL, default NOW() |

Index: `idx_applicants_kyc_status`

### credit_scores

| Column | Type | Constraints |
|--------|------|-------------|
| applicant_id | UUID | PK, FK → applicants |
| bureau_score | INT | NOT NULL, CHECK (300–900) |
| bureau_name | TEXT | NOT NULL |
| report_date | DATE | NOT NULL |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

### transactions

| Column | Type | Constraints |
|--------|------|-------------|
| txn_id | UUID | PK |
| applicant_id | UUID | NOT NULL, FK → applicants |
| txn_date | DATE | NOT NULL |
| amount | NUMERIC | NOT NULL, >= 0 |
| txn_type | TEXT | NOT NULL, CHECK (credit, debit) |
| category | TEXT | NOT NULL |
| merchant | TEXT | — |
| created_at | TIMESTAMP | NOT NULL |

Index: `idx_transactions_applicant_date`

### loans

| Column | Type | Constraints |
|--------|------|-------------|
| loan_id | UUID | PK |
| applicant_id | UUID | NOT NULL, FK → applicants |
| loan_type | TEXT | NOT NULL |
| principal_amount | NUMERIC | NOT NULL, >= 0 |
| outstanding_amount | NUMERIC | NOT NULL, >= 0, <= principal |
| interest_rate | NUMERIC | NOT NULL, >= 0 |
| status | TEXT | NOT NULL, CHECK (active, closed) |
| start_date | DATE | NOT NULL |
| created_at | TIMESTAMP | NOT NULL |

Index: `idx_loans_applicant`

### collateral

| Column | Type | Constraints |
|--------|------|-------------|
| collateral_id | UUID | PK |
| loan_id | UUID | NOT NULL, FK → loans |
| asset_type | TEXT | NOT NULL |
| asset_value | NUMERIC | NOT NULL, >= 0 |
| valuation_date | DATE | NOT NULL |
| created_at | TIMESTAMP | NOT NULL |

Index: `idx_collateral_loan`

### documents

| Column | Type | Constraints |
|--------|------|-------------|
| document_id | UUID | PK |
| applicant_id | UUID | NOT NULL, FK → applicants |
| document_type | TEXT | NOT NULL, CHECK (payslip, bank_statement, employment_letter) |
| extracted_income | NUMERIC | NOT NULL |
| verified | BOOLEAN | NOT NULL |
| document_date | DATE | NOT NULL |
| created_at | TIMESTAMP | NOT NULL |

Index: `idx_documents_applicant`

## Backend Schemas

### loan_agent/agent/schemas.py

**LoanSelectionOption**: `loan_id`, `loan_type`, `outstanding_amount`, `status`, `start_date`

**ToolCallTrace**: `step`, `tool`, `args`, `status`, `attempts`, `error?`, `result`

**UnderwritingAgentOutput**: `applicant_id`, `credit_risk`, `cashflow_signal`, `collateral_status`, `overall_risk_level`, `recommendation`, `explanation`, `tool_failed`, `missing_data`, `loan_selection_required`, `loan_options`, `selected_loan_id`, `tool_call_sequence`, `llm_outcome_analysis`

### loan_agent/agent/context.py

**IntentOutput**: `intent_type`, `entities`, `needs_clarification`, `clarification_question?`

**PlanningOutput**: `tool_horizon` (list of tool names), `notes?`

**TraceStep**: `step_type`, `step_index`, `detail`

**ToolHistoryEntry**: `tool`, `args`, `result`, `status`, `attempts`, `error?`

**AgentContext**: See agent.md for full fields.

### API Pydantic Models (server.py)

`ApplicantSummary`, `CreditRiskReq`, `CashflowReq`, `ListLoansReq`, `AssessCollateralReq`, `UnderwritingReq`, `AgentContinueReq`, `AgentChatReq`

## Frontend Types (App.tsx)

- **Applicant**: `applicant_id`, `full_name`, `annual_income`, `kyc_status`
- **LoanChoice**: `loan_id`, `loan_type`, `outstanding_amount`, `status`, `start_date`
- **ToolCallTrace**: `step`, `tool`, `args`, `status`, `attempts`, `error?`, `result`
- **LlmOutcomeAnalysis**: `approval_summary`, `decision`, `overall_risk_level`, `key_strengths`, `key_risks`, `next_actions`, `customer_information_used`, `analysis_findings`, `final_verdict`
- **AgentTraceStep**: `step_index`, `step_type`, `detail`
- **ClarificationOption**: `applicant_id`, `full_name`
- **ChatMessage**: `from` (user|agent), `text`
- **AgentResult**: Union of underwriting output fields + `agent_mode`, `agent_trace`, `clarification_question`, `clarification_options`, etc.
