"""Core agent: runs the LangGraph and maps result to AgentState (backward-compatible)."""

from __future__ import annotations

from typing import Any, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable

from agentic_app.agent.prompt import SYSTEM_PROMPT
from agentic_app.agent.state import AgentState, TraceStep
from agentic_app.config import settings
from agentic_app.graph import build_executor_graph, build_graph
from agentic_app.guardrails import input_guard
from agentic_app.memory import ConversationMemory


class Agent:
    """Runs the LangGraph agent and returns the same AgentState interface as before."""

    def __init__(
        self,
        llm: Optional[Runnable] = None,
        memory: Optional[ConversationMemory] = None,
    ) -> None:
        self._llm = llm
        self._memory = memory

    def run(self, user_input: str) -> AgentState:
        if settings.enable_guards:
            ok, err = input_guard(user_input)
            if not ok:
                return AgentState(
                    user_input=user_input,
                    final_response=err or "Input validation failed.",
                    trace_steps=[
                        TraceStep(step="received_input", info={"user_input": user_input}),
                        TraceStep(step="input_guard_error", info={"error": err}),
                    ],
                )

        if getattr(settings, "enable_planning", False):
            return self._run_with_outer_graph(user_input)
        return self._run_single(user_input, use_memory=True)

    def _build_initial_messages(self, user_input: str, use_memory: bool) -> tuple[List[BaseMessage], HumanMessage]:
        system = SystemMessage(content=SYSTEM_PROMPT)
        history: List[BaseMessage] = []
        if use_memory and self._memory and settings.enable_memory:
            history = self._memory.get_messages()
        current = HumanMessage(content=user_input)
        initial_messages: List[BaseMessage] = [system] + history + [current]
        return initial_messages, current

    def _map_result_to_agent_state(self, user_input: str, result: dict[str, Any]) -> AgentState:
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

    def _run_single(self, user_input: str, use_memory: bool) -> AgentState:
        graph = build_executor_graph(llm=self._llm)
        initial_messages, current = self._build_initial_messages(user_input, use_memory=use_memory)

        initial: dict[str, Any] = {
            "messages": initial_messages,
            "trace": [{"step": "received_input", "info": {"user_input": user_input}}],
            "steps": 0,
        }
        result = graph.invoke(initial)

        if use_memory and self._memory and settings.enable_memory:
            self._memory.append([current] + (result.get("messages") or []))

        return self._map_result_to_agent_state(user_input, result)

    def _run_with_outer_graph(self, user_input: str) -> AgentState:
        """Run with full planner → executor → validator → replanner → finalize graph."""
        graph = build_graph(llm=self._llm)
        initial_messages, current = self._build_initial_messages(user_input, use_memory=True)

        initial: dict[str, Any] = {
            "messages": initial_messages,
            "trace": [{"step": "received_input", "info": {"user_input": user_input}}],
            "steps": 0,
            "plan_status": "not_planned",
        }
        result = graph.invoke(initial)

        if self._memory and settings.enable_memory:
            self._memory.append([current] + (result.get("messages") or []))

        return self._map_result_to_agent_state(user_input, result)
