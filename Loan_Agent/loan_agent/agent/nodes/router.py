"""
Router Node: select the next tool to run (exactly one) or route to Decision.

Uses planning.tool_horizon and tool_history to pick the next eligible tool that
has not yet been run. Dynamically discovers tools from the registry. Single-loan only.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from loan_agent.agent.context import AgentContext

logger = logging.getLogger(__name__)

# Which tool fills which signal (for knowing what we already have)
TOOL_TO_SIGNAL = {
    "calculate_credit_risk": "credit_risk",
    "analyze_cashflow": "cashflow_signal",
    "list_applicant_loans": "_loans",  # not a final signal; we use it to get loan_id
    "assess_collateral": "collateral_status",
}


def run_router_node(ctx: AgentContext) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Returns ("decision", None) to go to Decision node, or ("tool", {"name": str, "args": dict}).
    """
    if not ctx.planning or not ctx.planning.tool_horizon:
        return "decision", None

    horizon = ctx.planning.tool_horizon
    already_run = {e.tool for e in ctx.tool_history}
    signals = ctx.signals
    applicant_id = ctx.applicant_id
    months = ctx.months
    loan_id = ctx.loan_id

    for tool_name in horizon:
        if tool_name in already_run:
            continue
        # assess_collateral needs loan_id; if we don't have it yet we might get it from list_applicant_loans
        if tool_name == "assess_collateral":
            if not loan_id and "list_applicant_loans" in already_run:
                # Get loan_id from last list_applicant_loans result
                for e in reversed(ctx.tool_history):
                    if e.tool == "list_applicant_loans":
                        choices = e.result.get("loan_choices", [])
                        if len(choices) == 1:
                            loan_id = choices[0].get("loan_id")
                            if loan_id:
                                signals["_loan_id"] = loan_id
                        break
            if not loan_id:
                # Run list_applicant_loans first if not yet run
                if "list_applicant_loans" not in already_run:
                    return "tool", _args_for("list_applicant_loans", applicant_id, months, None)
                continue  # multiple or zero loans; skip collateral for single-loan we assume one
        args = _args_for(tool_name, applicant_id, months, loan_id)
        if args is None:
            continue
        logger.info("checkpoint: router selected tool", extra={"tool": tool_name})
        return "tool", {"name": tool_name, "args": args}

    return "decision", None


def _args_for(tool_name: str, applicant_id: Optional[str], months: int, loan_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if tool_name == "calculate_credit_risk":
        return {"applicant_id": applicant_id} if applicant_id else None
    if tool_name == "analyze_cashflow":
        return {"applicant_id": applicant_id, "months": months} if applicant_id else None
    if tool_name == "list_applicant_loans":
        return {"applicant_id": applicant_id} if applicant_id else None
    if tool_name == "assess_collateral":
        return {"loan_id": loan_id} if loan_id else None
    return None
