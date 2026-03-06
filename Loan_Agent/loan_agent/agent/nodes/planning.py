"""
Planning Node: determine what information is needed and which tools are eligible.

Produces a tool horizon (list of tool names, no order). Router will select the next
tool from this horizon based on current context. Single-loan flow.
"""
from __future__ import annotations

import logging
from typing import List

from loan_agent.agent.context import AgentContext, PlanningOutput
from loan_agent.tool_registry import list_tools

logger = logging.getLogger(__name__)

# Intent -> tool names that can provide required signals (order is not fixed; Router decides)
INTENT_TOOL_HORIZON = {
    "full_underwriting": [
        "calculate_credit_risk",
        "analyze_cashflow",
        "list_applicant_loans",
        "assess_collateral",
    ],
    "credit_only": ["calculate_credit_risk"],
    # general_question uses no tools by default (LLM-only answer)
    "general_question": [],
    # customer_chat uses tools opportunistically to answer questions about a
    # specific applicant (credit, cashflow, loans, collateral).
    "customer_chat": [
        "calculate_credit_risk",
        "analyze_cashflow",
        "list_applicant_loans",
        "assess_collateral",
    ],
}


def run_planning_node(ctx: AgentContext) -> None:
    """
    Set ctx.planning from intent and registry. Only includes tools that exist in the registry.
    """
    intent_type = (ctx.intent and ctx.intent.intent_type) or "full_underwriting"
    horizon = INTENT_TOOL_HORIZON.get(intent_type, INTENT_TOOL_HORIZON["full_underwriting"])
    registered = {t.name for t in list_tools()}
    eligible = [t for t in horizon if t in registered]
    ctx.planning = PlanningOutput(tool_horizon=eligible, notes=f"Intent: {intent_type}")
    ctx.append_trace("plan", {"tool_horizon": eligible, "intent_type": intent_type})
    ctx.agent_state = "planning"
    logger.info("checkpoint: plan created", extra={"tool_horizon": eligible})
