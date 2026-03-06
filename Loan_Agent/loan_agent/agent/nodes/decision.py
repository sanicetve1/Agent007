"""
Decision Node: final underwriting recommendation via deterministic policy; LLM for explanation only.

Uses merge_underwriting_signals on context.signals, then attaches LLM summary.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from loan_agent.agent.context import AgentContext
from loan_agent.agent.policy import merge_underwriting_signals

# Avoid circular import: use runner's LLM helpers when calling from autonomous flow
from loan_agent.agent import runner as _runner_module

logger = logging.getLogger(__name__)


def run_decision_node(ctx: AgentContext, model: str = "gpt-4.1-mini") -> None:
    """
    Compute policy decision from ctx.signals, set ctx.policy_decision, ctx.llm_explanation, ctx.llm_outcome_analysis.
    """
    credit_risk = ctx.signals.get("credit_risk") or {}
    cashflow_signal = ctx.signals.get("cashflow_signal") or {}
    collateral_status = ctx.signals.get("collateral_status") or {}
    tool_failed = any(e.status != "success" for e in ctx.tool_history)

    overall, recommendation, explanation, missing_data = merge_underwriting_signals(
        credit_risk=credit_risk,
        cashflow_signal=cashflow_signal,
        collateral_status=collateral_status,
        tool_failed=tool_failed,
    )

    ctx.policy_decision = {
        "overall_risk_level": overall,
        "recommendation": recommendation,
        "explanation": explanation,
        "missing_data": missing_data,
        "tool_failed": tool_failed,
    }

    applicant_id = ctx.applicant_id or ""
    explanation_text = _runner_module._render_explanation_with_sdk(
        applicant_id=applicant_id,
        credit=credit_risk,
        cashflow=cashflow_signal,
        collateral=collateral_status,
        overall_risk_level=overall,
        recommendation=recommendation,
        model=model,
    )
    ctx.llm_explanation = explanation_text or explanation

    payload: Dict[str, Any] = {
        "applicant_id": applicant_id,
        "credit_risk": credit_risk,
        "cashflow_signal": cashflow_signal,
        "collateral_status": collateral_status,
        "overall_risk_level": overall,
        "recommendation": recommendation,
        "tool_failed": tool_failed,
        "missing_data": missing_data,
        "tool_call_sequence": [
            {"step": i + 1, "tool": e.tool, "args": e.args, "status": e.status, "attempts": e.attempts, "error": e.error, "result": e.result}
            for i, e in enumerate(ctx.tool_history)
        ],
        "explanation": ctx.llm_explanation,
    }
    ctx.llm_outcome_analysis = _runner_module._render_outcome_analysis_with_sdk(payload=payload, model=model)
    ctx.agent_state = "done"
    ctx.append_trace("decision", {"recommendation": recommendation, "overall_risk_level": overall})
    logger.info("checkpoint: decision", extra={"recommendation": recommendation})
