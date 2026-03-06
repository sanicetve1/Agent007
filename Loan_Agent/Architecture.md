OpenAI Responses API + Custom Agent Framework
Use the OpenAI Responses API and implement the ReAct agent loop in our own code
following are the core premitives 
Agent
Runner
Router
Context
Tool
StateMachine
RetryEngine



loan_agent/

agent/
    agent.py
    runner.py
    router.py
    context.py
    state_machine.py

tools/
    credit_risk_tool.py
    cashflow_tool.py
    collateral_tool.py

api/
    underwriting_routes.py

models/
    loan_models.py

db/
    postgres.py

configs/
    agent_rules.py

need a Tool Registry + Dynamic Tool Discovery.

Without this, every new tool requires rewriting the router.

A proper system looks like:

Clarification flow (spec)
When we ask

Only after Intent.
Trigger: missing a required entity for that intent (e.g. applicant_id).
Out of scope for now: multiple loans; assume single loan only.
What we do with the user’s reply

Open-ended reply → re-run Intent (e.g. treat reply as additional user input and re-extract intent + entities).
Direct entity reply (e.g. user sends a loan_id or applicant_id) → update context.entities and resume from Planning (no Intent re-run).
Session/context

One session_id (or context_id) per conversation.
Backend persists AgentContext (or a minimal checkpoint) keyed by session_id.
When the user replies, backend loads context by session_id, applies the reply (update entities or re-run Intent as above), then continues (re-run from Intent or resume from Planning).
Flow

User sends request → Intent runs → missing entity → return clarification_needed + question + session_id.
UI shows chat; user replies.
Client sends reply with same session_id.
Backend loads context, applies reply (update entities or re-run Intent), then either resumes from Planning or re-runs from Intent.
