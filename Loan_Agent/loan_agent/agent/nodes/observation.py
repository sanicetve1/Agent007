"""
Observation Node: collect tool output and update agent context (tool_history + signals).

Maps tool results into context.signals for use by Reasoning and Decision. Single-loan:
when list_applicant_loans returns one loan, we set signals["_loan_id"] for assess_collateral.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from loan_agent.agent.context import AgentContext

logger = logging.getLogger(__name__)


def run_observation_node(
    ctx: AgentContext,
    tool_name: str,
    args: Dict[str, Any],
    result: Dict[str, Any],
    status: str,
    attempts: int = 1,
    error: str | None = None,
) -> None:
    """
    Append tool execution to tool_history and update signals from the result.
    """
    ctx.append_tool_entry(tool=tool_name, args=args, result=result, status=status, attempts=attempts, error=error)
    ctx.append_trace("observation", {"tool": tool_name, "status": status})

    if tool_name == "calculate_credit_risk" and status == "success":
        ctx.signals["credit_risk"] = result
    elif tool_name == "analyze_cashflow" and status == "success":
        ctx.signals["cashflow_signal"] = result
    elif tool_name == "list_applicant_loans" and status == "success":
        choices = result.get("loan_choices", [])
        if len(choices) == 1:
            ctx.signals["_loan_id"] = choices[0].get("loan_id")
    elif tool_name == "assess_collateral" and status == "success":
        ctx.signals["collateral_status"] = result

    ctx.agent_state = "observing"
    logger.info("checkpoint: observation", extra={"tool": tool_name, "status": status})
