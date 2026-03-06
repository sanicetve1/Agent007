"""
State machine: orchestrates the ReAct agent graph.

Flow: Intent -> (clarification?) -> Planning -> [Router -> Tool -> Observation -> Reasoning]*
-> Decision. Nodes only read/write context; no direct node-to-node calls.
Checkpoint logging at each step. Stops on goal_met, max_steps, or Router returns decision.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from loan_agent.agent.context import AgentContext
from loan_agent.agent.nodes import (
    run_decision_node,
    run_intent_node,
    run_observation_node,
    run_planning_node,
    run_reasoning_node,
    run_router_node,
)
from loan_agent.tool_registry import execute_tool

logger = logging.getLogger(__name__)


def _run_tool_with_retry(name: str, args: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """Execute a registered tool with one retry on failure."""
    last_error: Optional[Exception] = None
    for attempt in range(2):
        try:
            return execute_tool(name, **args), None, attempt + 1
        except Exception as exc:
            last_error = exc
    return None, str(last_error) if last_error else "Unknown tool error", 2


def run_react_loop(
    ctx: AgentContext,
    max_steps: int,
    model: str = "gpt-4.1-mini",
    prefilled_entities: Optional[Dict[str, Any]] = None,
    skip_intent: bool = False,
) -> None:
    """
    Run the ReAct loop. Updates ctx in place. If ctx.clarification_required is set
    after Intent, returns without running the rest (caller returns to client).
    When skip_intent=True (e.g. resuming after clarification), start from Planning.
    """
    if not skip_intent:
        if prefilled_entities is not None:
            ctx._prefilled_entities = prefilled_entities  # type: ignore[attr-defined]
        run_intent_node(ctx, model=model)
        if ctx.clarification_required:
            logger.info("checkpoint: stopping for clarification")
            return

    run_planning_node(ctx)
    steps = 0
    while steps < max_steps:
        route, payload = run_router_node(ctx)
        if route == "decision":
            break
        if route != "tool" or not payload:
            break
        tool_name = payload.get("name")
        tool_args = payload.get("args") or {}
        if not tool_name:
            break

        result, err, attempts = _run_tool_with_retry(tool_name, tool_args)
        status = "success" if err is None else "failed"
        run_observation_node(
            ctx,
            tool_name=tool_name,
            args=tool_args,
            result=result or {},
            status=status,
            attempts=attempts,
            error=err,
        )
        steps += 1

        run_reasoning_node(ctx)
        if ctx.goal_met:
            logger.info("checkpoint: goal_met, proceeding to decision")
            break
        if steps >= max_steps:
            ctx.max_steps_reached = True
            logger.info("checkpoint: max_steps reached", extra={"max_steps": max_steps})
            break
        run_planning_node(ctx)

    run_decision_node(ctx, model=model)
