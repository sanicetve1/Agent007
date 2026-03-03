from __future__ import annotations

from operator import add
from typing import Annotated, Any, Dict, List, Optional, TypedDict, Literal

from langchain_core.messages import BaseMessage

from agentic_app.agent.planner import PlanStep


class GraphState(TypedDict, total=False):
    """LangGraph state: messages and trace use add reducer for multi-step evolution."""

    messages: Annotated[List[BaseMessage], add]
    trace: Annotated[List[Dict[str, Any]], add]
    # Bounded reasoning loop counter
    steps: int
    last_tool_name: Optional[str]
    last_tool_args: Dict[str, Any]
    last_tool_result: Any
    error: Optional[str]

    # Planning-related fields
    plan: List[PlanStep]
    current_step_index: int
    plan_status: Literal["not_planned", "planned", "executing", "done", "failed"]
    validation_result: Optional[Dict[str, Any]]
    replan_reason: Optional[str]
