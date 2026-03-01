from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TraceStep:
    step: str
    info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentState:
    user_input: str
    intent_summary: Optional[str] = None
    selected_tool: Optional[str] = None
    tool_args: Dict[str, Any] = field(default_factory=dict)
    tool_result: Optional[Any] = None
    final_response: Optional[str] = None
    trace_steps: List[TraceStep] = field(default_factory=list)

    def add_step(self, step: str, **info: Any) -> None:
        self.trace_steps.append(TraceStep(step=step, info=info))

