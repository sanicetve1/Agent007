"""
Autonomous ReAct agent entry point.

When ENABLE_AUTONOMY=true, the API calls this. Runs the full ReAct loop
(Intent → Planning → Router → Tools → Observation → Reasoning → Decision)
and returns a response in the same shape as the deterministic runner for UI compatibility.
Supports clarification flow: when Intent needs a missing entity, returns clarification_needed
and persists context by session_id; /agent/continue with session_id + user_reply resumes.
"""
from __future__ import annotations

import copy
import logging
import re
from typing import Any, Dict, List, Optional

from loan_agent.agent.context import AgentContext, IntentOutput
from loan_agent.agent.state_machine import run_react_loop
from loan_agent.applicants import resolve_applicants_by_name
from loan_agent.config import agent_settings
from loan_agent.tools import (  # noqa: F401 - ensure tools are registered
    analyze_cashflow,
    assess_collateral,
    calculate_credit_risk,
    list_applicant_loans,
)

logger = logging.getLogger(__name__)

# In-memory session store for clarification flow (production would use Redis/DB)
_session_store: Dict[str, AgentContext] = {}

UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def run_autonomous_underwriting_agent(
    applicant_id: str,
    loan_id: Optional[str] = None,
    months: int = 6,
    model: str = "gpt-4.1-mini",
    session_id: Optional[str] = None,
    user_request: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Run the autonomous ReAct underwriting agent. Uses AgentContext and state machine.
    Returns the same response shape as run_underwriting_agent for UI compatibility.
    """
    prefilled = {
        "applicant_id": applicant_id or "",
        "loan_id": loan_id,
        "months": months,
    }
    ctx_kw: Dict[str, Any] = {
        "user_request": user_request or f"Full underwriting for applicant {applicant_id or '(please provide)'}",
    }
    if session_id:
        ctx_kw["session_id"] = session_id
    ctx = AgentContext(**ctx_kw)
    max_steps = getattr(agent_settings, "max_steps", 8)

    run_react_loop(ctx, max_steps=max_steps, model=model, prefilled_entities=prefilled)

    if ctx.clarification_required:
        _session_store[ctx.session_id] = copy.deepcopy(ctx)
        return _response_clarification(ctx)

    return _response_from_context(ctx, applicant_id or ctx.applicant_id or "", loan_id)


def run_autonomous_continue(
    session_id: str,
    user_reply: str,
    model: str = "gpt-4.1-mini",
) -> Dict[str, Any]:
    """
    Continue after clarification: load context, apply user reply, then run from Planning
    (or re-run Intent for open-ended reply). Direct entity reply (e.g. applicant_id UUID)
    updates entities and resumes from Planning; otherwise re-run Intent with reply as user_request.
    """
    ctx = _session_store.pop(session_id, None)
    if ctx is None:
        return {
            "status": "error",
            "error": "session_expired",
            "message": "Session not found or expired. Start a new underwriting request.",
        }
    ctx = copy.deepcopy(ctx)
    ctx.clarification_required = False
    ctx.clarification_question = None
    max_steps = getattr(agent_settings, "max_steps", 8)

    reply = (user_reply or "").strip()
    applicant_id_resolved: Optional[str] = None

    if UUID_PATTERN.match(reply):
        applicant_id_resolved = reply
    else:
        # Resolve by customer name (MVP: unique names or disambiguate by listing)
        matches: List[Dict[str, Any]] = resolve_applicants_by_name(reply)
        if len(matches) == 0:
            _session_store[ctx.session_id] = copy.deepcopy(ctx)
            return _response_clarification(
                ctx,
                clarification_question="No customer found with that name. Please provide a valid customer name or applicant ID (UUID).",
            )
        if len(matches) == 1:
            applicant_id_resolved = matches[0]["applicant_id"]
        else:
            _session_store[ctx.session_id] = copy.deepcopy(ctx)
            names_list = "; ".join(f"{m['full_name']} ({m['applicant_id'][:8]}...)" for m in matches)
            return _response_clarification(
                ctx,
                clarification_question=f"Multiple customers found. Which one? Type the full name or applicant ID: {names_list}",
                clarification_options=matches,
            )

    if applicant_id_resolved:
        ctx.intent = IntentOutput(
            intent_type="full_underwriting",
            entities={"applicant_id": applicant_id_resolved, "loan_id": None, "months": 6},
            needs_clarification=False,
            clarification_question=None,
        )
        run_react_loop(ctx, max_steps=max_steps, model=model, skip_intent=True)
        return _response_from_context(ctx, applicant_id_resolved, ctx.loan_id)

    ctx.user_request = (ctx.user_request or "") + "\nUser: " + reply
    ctx._prefilled_entities = {}  # type: ignore[attr-defined]
    run_intent_node_from_runner(ctx, model=model)
    if ctx.clarification_required:
        _session_store[ctx.session_id] = copy.deepcopy(ctx)
        return _response_clarification(ctx)
    run_react_loop(ctx, max_steps=max_steps, model=model, skip_intent=True)
    return _response_from_context(ctx, ctx.applicant_id or "", ctx.loan_id)


def run_intent_node_from_runner(ctx: AgentContext, model: str) -> None:
    """Re-run Intent only (used when user sends open-ended reply)."""
    from loan_agent.agent.nodes import run_intent_node
    run_intent_node(ctx, model=model, user_request=ctx.user_request)


def _response_clarification(
    ctx: AgentContext,
    clarification_question: Optional[str] = None,
    clarification_options: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Return a response indicating clarification is needed (same shape, with status)."""
    return {
        "status": "clarification_needed",
        "clarification_question": clarification_question or ctx.clarification_question,
        "session_id": ctx.session_id,
        **({"clarification_options": clarification_options} if clarification_options is not None else {}),
        "applicant_id": ctx.applicant_id,
        "overall_risk_level": "medium",
        "recommendation": "conditional",
        "explanation": "Waiting for user input.",
        "tool_failed": False,
        "missing_data": [],
        "loan_selection_required": False,
        "loan_options": [],
        "selected_loan_id": None,
        "tool_call_sequence": [],
        "llm_outcome_analysis": {},
        "agent_mode": "autonomous",
        "agent_trace": [{"step_index": t.step_index, "step_type": t.step_type, "detail": t.detail} for t in ctx.trace],
    }


def _response_from_context(
    ctx: AgentContext,
    applicant_id: str,
    loan_id: Optional[str],
) -> Dict[str, Any]:
    """Build UI-shaped response from AgentContext after Decision node."""
    policy = ctx.policy_decision
    signals = ctx.signals
    tool_call_sequence = [
        {
            "step": i + 1,
            "tool": e.tool,
            "args": e.args,
            "status": e.status,
            "attempts": e.attempts,
            "error": e.error,
            "result": e.result,
        }
        for i, e in enumerate(ctx.tool_history)
    ]
    agent_trace = [
        {"step_index": t.step_index, "step_type": t.step_type, "detail": t.detail}
        for t in ctx.trace
    ]

    out = {
        "applicant_id": applicant_id,
        "credit_risk": signals.get("credit_risk", {}),
        "cashflow_signal": signals.get("cashflow_signal", {}),
        "collateral_status": signals.get("collateral_status", {}),
        "overall_risk_level": policy.get("overall_risk_level", "medium"),
        "recommendation": policy.get("recommendation", "conditional"),
        "explanation": ctx.llm_explanation or policy.get("explanation", ""),
        "tool_failed": policy.get("tool_failed", False),
        "missing_data": policy.get("missing_data", []),
        "loan_selection_required": False,
        "loan_options": [],
        "selected_loan_id": loan_id,
        "tool_call_sequence": tool_call_sequence,
        "llm_outcome_analysis": ctx.llm_outcome_analysis,
        "agent_mode": "autonomous",
        "agent_trace": agent_trace,
    }
    if getattr(ctx, "max_steps_reached", False):
        out["max_steps_reached"] = True
        out["explanation"] = (out["explanation"] or "") + " (Stopped after max steps; partial assessment.)"
    return out
