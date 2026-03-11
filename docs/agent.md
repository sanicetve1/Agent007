# Loan Underwriting Agent

The Loan Agent evaluates loan applicants by orchestrating risk analysis tools. It follows a Node + Edge graph model with two execution modes.

## Agent Modes

| Mode | Trigger | Description |
|------|---------|-------------|
| **Deterministic** | `ENABLE_AUTONOMY=false` | Fixed tool order: credit_risk → cashflow → list_applicant_loans → assess_collateral. No LLM for routing; decision via policy merge. |
| **Autonomous** | `ENABLE_AUTONOMY=true` | ReAct loop: Intent → Planning → Router → Tool → Observation → Reasoning → Decision. LLM selects tools; Decision node produces final output. |

Mode is configured via `ENABLE_AUTONOMY` in config; see `loan_agent/config.py`.

## Node Architecture

Nodes read from and write to `AgentContext`. The state machine drives flow; no direct node-to-node calls.

| Node | Responsibility |
|------|----------------|
| **Intent** | Parse user request; extract entities (applicant_id, loan_id, months). Sets `clarification_required` when applicant_id is missing. |
| **Planning** | Determine `tool_horizon` (eligible tools). |
| **Router** | Pick next tool from horizon (excluding already-run tools). Ensures `list_applicant_loans` before `assess_collateral` when loan_id missing. |
| **Tool** | Execute via `tool_registry.execute_tool` with retry (2 attempts). |
| **Observation** | Append tool result to `tool_history`; update `signals`. |
| **Reasoning** | LLM analyzes collected data; may set `goal_met`, `confidence`. |
| **Decision** | Final recommendation via `merge_underwriting_signals` (policy) or LLM; populate `policy_decision`, `llm_explanation`. |

## Context Model

`AgentContext` (see `loan_agent/agent/context.py`) holds:

- **User input**: `user_request`, `session_id`
- **Extracted**: `intent` (IntentOutput), `planning` (PlanningOutput), `tool_history`, `signals` (credit_risk, cashflow_signal, collateral_status)
- **Outputs**: `policy_decision`, `llm_explanation`, `llm_outcome_analysis`
- **Chat**: `chat_answer` (for customer chat mode)
- **Control**: `trace`, `agent_state`, `clarification_required`, `clarification_question`, `goal_met`, `confidence`, `max_steps_reached`

## Clarification Flow

Trigger: Intent node finds missing required entity (e.g. `applicant_id`).

1. Agent returns `status: "clarification_needed"` with `session_id` and `clarification_question`.
2. Client sends `/agent/continue` with `session_id` and `user_reply`.
3. Backend loads context; if reply is UUID or resolvable name → update entities, resume from Planning; else re-run Intent with reply as user_request.

## Customer Chat Mode

`run_customer_chat` (autonomous only) runs a lightweight ReAct loop in `customer_chat` intent. Tools are called when needed; the Decision node produces a natural-language `chat_answer` in `ctx.chat_answer` instead of a full underwriting decision. One logical chat session per applicant is tracked via `session_id`.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_AUTONOMY` | `false` | Use autonomous ReAct agent vs deterministic pipeline. |
| `AGENT_MAX_STEPS` | `8` | Max tool-execution steps in autonomous mode before forcing decision or informing user. |
