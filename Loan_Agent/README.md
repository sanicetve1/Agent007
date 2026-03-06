# Loan Agent (Reusable Tool-First Skeleton)

This folder contains a reusable tool layer for building an underwriting agent with a GPT SDK style workflow.

Current scope:
- Dockerized Postgres database for local development
- Seeded underwriting sample data
- Deterministic underwriting tool: `calculate_credit_risk`
- Deterministic underwriting tool: `analyze_cashflow`
- Deterministic underwriting tool: `list_applicant_loans`
- Deterministic underwriting tool: `assess_collateral`
- ReAct-style underwriting runner with retry-once and structured output

Design goal:
- Keep tools deterministic and auditable
- Keep tool contracts stable
- Make domain logic swappable in the future without rewriting the whole agent stack

## Project Layout

`Loan_Agent/`
- `docker-compose.yaml` - Postgres + pgAdmin
- `DB/init.sql/init.sql` - schema and seed data
- `setup_db.ps1` - local DB bootstrap helper
- `loan_agent/` - reusable Python package
  - `config.py` - environment configuration
  - `db.py` - DB connection helper
  - `tool_registry.py` - lightweight reusable tool registry
  - `agent/`
    - `runner.py` - underwriting ReAct flow runtime
    - `policy.py` - deterministic risk merge policy
    - `schemas.py` - structured output model
  - `tools/`
    - `calculate_credit_risk.py` - deterministic underwriting risk tool
    - `analyze_cashflow_stability.py` - cashflow signal tool (`analyze_cashflow`)
    - `list_applicant_loans.py` - loan selection helper
    - `assess_collateral.py` - collateral adequacy tool

## Prerequisites

- Python 3.11+
- Docker Desktop
- Postgres container running from this folder

Install package dependencies:

```powershell
pip install -r requirements.txt
```

## Environment Variables

Set these in your shell or `.env` file:

```env
LOAN_DB_HOST=localhost
LOAN_DB_PORT=5432
LOAN_DB_NAME=loan_db
LOAN_DB_USER=admin
LOAN_DB_PASSWORD=change_me

# Agent mode: false = deterministic pipeline (fixed tool order); true = autonomous ReAct agent (stub until implemented)
ENABLE_AUTONOMY=false
```

## Start Database + GUI

From `Loan_Agent/`:

```powershell
docker compose up -d
```

pgAdmin:
- URL: `http://localhost:5050`
- Email: `admin@loanagent.com`
- Password: set `PGADMIN_DEFAULT_PASSWORD` in your local env (e.g., `change_me`)

## Use the Tool (Python)

```python
from loan_agent.tools.calculate_credit_risk import calculate_credit_risk
from loan_agent.tools.analyze_cashflow_stability import analyze_cashflow
from loan_agent.tools.list_applicant_loans import list_applicant_loans
from loan_agent.tools.assess_collateral import assess_collateral

result = calculate_credit_risk("YOUR_APPLICANT_UUID")
print(result)

cashflow = analyze_cashflow("YOUR_APPLICANT_UUID", months=6)
print(cashflow)

loans = list_applicant_loans("YOUR_APPLICANT_UUID")
print(loans)

collateral = assess_collateral("YOUR_LOAN_UUID", threshold_ratio=1.0)
print(collateral)
```

Expected output shape:

```json
{
  "applicant_id": "UUID",
  "credit_score": 780,
  "dti": 0.35,
  "risk_level": "medium",
  "recommendation": "approve with conditions"
}
```

## Run Underwriting ReAct Agent

```python
from loan_agent.agent.runner import run_underwriting_agent

# First pass: no loan_id provided
first = run_underwriting_agent(applicant_id="YOUR_APPLICANT_UUID", months=6)
print(first)

# If first["loan_selection_required"] is true, pick one loan_id from first["loan_options"]
if first.get("loan_selection_required") and first.get("loan_options"):
    selected = first["loan_options"][0]["loan_id"]
    final = run_underwriting_agent(
        applicant_id="YOUR_APPLICANT_UUID",
        loan_id=selected,
        months=6,
        model="gpt-4.1-mini",
    )
    print(final)
```

Agent runtime behavior:
- Uses tools in order: `calculate_credit_risk` -> `analyze_cashflow` -> `list_applicant_loans` -> `assess_collateral`
- Retries each tool once on failure
- Marks `tool_failed` and `missing_data` if any step fails
- Returns final structured JSON plus explanation

## Autonomous ReAct agent (ENABLE_AUTONOMY=true)

When `ENABLE_AUTONOMY=true` in `.env`, `/agent/run` uses the ReAct loop instead of the fixed pipeline:

- **Intent** → extract intent and entities (or ask for clarification if e.g. `applicant_id` missing).
- **Planning** → build tool horizon from registry (no fixed order).
- **Router** → pick one tool per step; **Observation** → update context; **Reasoning** → set `goal_met` / confidence.
- **Decision** → deterministic policy + LLM explanation only.

Flow: Intent → Planning → [Router → Tool (with retry) → Observation → Reasoning] until `goal_met` or `AGENT_MAX_STEPS` → Decision.  
Response shape is the same as the deterministic runner, plus `agent_mode: "autonomous"` and `agent_trace` (intent, plan, tool, reasoning, decision steps) for the UI. Checkpoint logging at each step; optional persistence can be added via env.

## Run Loan Agent API (for React UI)

**You must run from the `Loan_Agent/` directory** so the `loan_agent` package is on the path:

```powershell
cd Loan_Agent
uv run --with fastapi --with "uvicorn[standard]" --with "psycopg[binary]" --with python-dotenv --with openai uvicorn loan_agent.api.server:app --reload --host 0.0.0.0 --port 8001
```

API docs:
- `http://localhost:8001/docs`

## Run React UI

From `agent-ui/`:

```powershell
npm install
npm run dev
```

Open:
- `http://localhost:5173`

The UI now supports:
- individual tool testing (`calculate_credit_risk`, `analyze_cashflow`, `list_applicant_loans`, `assess_collateral`)
- two use cases:
  - pre-screen agent run
  - full underwriting run

## Reusability Rules (Keep for Future Domains)

1. Keep every tool deterministic and side-effect free unless explicitly required.
2. Keep input/output schema stable and versionable.
3. Isolate domain logic in `tools/` only.
4. Keep DB and service access behind helper modules (`config.py`, `db.py`).
5. Register tools via a generic registry instead of hard-wiring to one domain.
6. If domain changes (e.g., insurance, fraud, collections), add new tool files and register them; do not rewrite the framework skeleton.
