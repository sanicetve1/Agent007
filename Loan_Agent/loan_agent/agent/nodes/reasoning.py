"""
Reasoning Node: analyze collected data and set goal_met / confidence.

Used by the state machine to decide: continue to next tool (Planning) or go to Decision.
Intent-dependent key signals: full_underwriting => credit_risk, cashflow_signal, collateral_status.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from loan_agent.agent.context import AgentContext

logger = logging.getLogger(__name__)

# Intent -> list of signal keys we need (from context.signals) to consider goal_met
INTENT_KEY_SIGNALS: Dict[str, List[str]] = {
    "full_underwriting": ["credit_risk", "cashflow_signal", "collateral_status"],
    "credit_only": ["credit_risk"],
    "general_question": [],
}


def run_reasoning_node(ctx: AgentContext) -> None:
    """
    Set ctx.goal_met and ctx.confidence from current signals and intent.
    """
    intent_type = (ctx.intent and ctx.intent.intent_type) or "full_underwriting"
    key_signals = INTENT_KEY_SIGNALS.get(intent_type, INTENT_KEY_SIGNALS["full_underwriting"])
    signals = ctx.signals

    have = sum(1 for k in key_signals if _has_signal(signals, k))
    total = len(key_signals)
    goal_met = total > 0 and have == total
    confidence = have / total if total else 1.0

    ctx.goal_met = goal_met
    ctx.confidence = confidence
    ctx.agent_state = "reasoning"
    ctx.append_trace("reasoning", {"goal_met": goal_met, "confidence": confidence, "signals_have": have, "signals_total": total})
    logger.info("checkpoint: reasoning", extra={"goal_met": goal_met, "confidence": confidence})


def _has_signal(signals: Dict[str, Any], key: str) -> bool:
    val = signals.get(key)
    if val is None:
        return False
    if isinstance(val, dict) and not val:
        return False
    return True
