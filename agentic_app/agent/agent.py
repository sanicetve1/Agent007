"""Core agent: runs the LangGraph and maps result to AgentState (backward-compatible)."""

from __future__ import annotations

from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable

from agentic_app.agent.prompt import SYSTEM_PROMPT
from agentic_app.agent.state import AgentState, TraceStep
from agentic_app.graph import build_graph


class Agent:
    """Runs the LangGraph agent and returns the same AgentState interface as before."""

    def __init__(self, llm: Optional[Runnable] = None) -> None:
        self._llm = llm

    def run(self, user_input: str) -> AgentState:
        graph = build_graph(llm=self._llm)
        initial: dict[str, Any] = {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_input),
            ],
            "trace": [{"step": "received_input", "info": {"user_input": user_input}}],
            "steps": 0,
        }
        result = graph.invoke(initial)

        trace_steps = [
            TraceStep(step=t["step"], info=t.get("info", {}))
            for t in (result.get("trace") or [])
            if isinstance(t, dict)
        ]

        messages = result.get("messages") or []
        if result.get("error"):
            final_response = result["error"]
        elif messages:
            last = messages[-1]
            final_response = getattr(last, "content", None) or ""
        else:
            final_response = ""

        return AgentState(
            user_input=user_input,
            selected_tool=result.get("last_tool_name"),
            tool_args=result.get("last_tool_args") or {},
            tool_result=result.get("last_tool_result"),
            final_response=final_response,
            trace_steps=trace_steps,
        )
