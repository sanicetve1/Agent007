# Tools

## Tool Registry

The tool registry (`loan_agent/tool_registry.py`) provides:

- **ToolSpec**: `name`, `description`, `input_schema` (JSON Schema), `fn` (callable)
- **register_tool(spec)**: Register a tool by name
- **get_tool(name)**, **list_tools()**: Lookup and enumerate
- **execute_tool(name, **kwargs)**: Invoke registered tool
- **to_openai_function_tools()**: Return OpenAI-style function tool descriptors for SDK wiring

Tools are registered on import via `loan_agent/tools/__init__.py`.

## Registered Tools

### 1. calculate_credit_risk

**Purpose**: Compute credit risk using DTI and bureau score.

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| applicant_id | string (UUID) | yes | Applicant identifier |

**Output**: `applicant_id`, `credit_score`, `dti`, `risk_level` (low/medium/high), `recommendation`, `metadata`

**DB tables**: `applicants`, `credit_scores`, `loans` (active outstanding)

**Logic**: DTI = total_active_outstanding / annual_income. Risk classification by DTI + bureau score thresholds (e.g. DTI > 0.5 or score < 600 → high).

---

### 2. analyze_cashflow

**Purpose**: Analyze cashflow stability over recent N months.

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| applicant_id | string (UUID) | yes | Applicant identifier |
| months | int | no (default 6) | Months to analyze (1–24) |

**Output**: `applicant_id`, `months_analyzed`, `average_income`, `income_std_dev`, `average_expenses`, `debit_std_dev`, `net_cashflow`, `signals` (volatile_income, unstable_expenses, cashflow_deficit, payment_risk), `recommendation`, `metadata`

**DB tables**: `applicants`, `transactions`

**Logic**: Monthly aggregation of credits/debits; volatility ratios; EMI regularity. Recommendation: "high cashflow risk" / "moderate cashflow risk" / "stable cashflow".

---

### 3. list_applicant_loans

**Purpose**: List loans for an applicant (used before collateral assessment).

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| applicant_id | string (UUID) | yes | Applicant identifier |
| include_closed | bool | no (default false) | Include closed loans |

**Output**: `applicant_id`, `loan_choices` (array of loan_id, loan_type, outstanding_amount, status, start_date), `loan_count`, `requires_selection`, `recommended_loan_id`, `metadata`

**DB tables**: `applicants`, `loans`

---

### 4. assess_collateral

**Purpose**: Evaluate collateral adequacy for a loan.

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| loan_id | string (UUID) | yes | Loan identifier |
| threshold_ratio | float | no (default 1.0) | Coverage threshold (ratio >= threshold → adequate) |

**Output**: `loan_id`, `loan_type`, `principal_amount`, `outstanding_amount`, `collateral_count`, `total_collateral_value`, `coverage_ratio`, `threshold_ratio`, `collateral_status` (adequate/borderline/insufficient), `signals`, `recommendation`, `metadata`

**DB tables**: `loans`, `collateral`

**Logic**: coverage_ratio = total_collateral_value / outstanding_amount. Bands: adequate (≥ threshold), borderline (≥ 0.8), insufficient (< 0.8).

## Tool Category

All four tools are **data retrieval / deterministic analytical** tools. They query the database and apply rule-based logic. No external ML models or interpretative LLM calls within the tools themselves.
