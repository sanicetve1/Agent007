from __future__ import annotations

from operator import add
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage


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
