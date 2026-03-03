from __future__ import annotations

import json

from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

from agentic_app.agent import Agent
from agentic_app.agent.planner import plan_for_input
from agentic_app.config import settings


class _FakePlannerModel(Runnable):
    """Fake model that returns a fixed JSON plan for planning calls."""

    def invoke(self, input, config=None, **kwargs):
        # The planner always receives a list of messages.
        _ = input
        content = json.dumps(
            [
                {
                    "id": 1,
                    "description": "add 2 and 3",
                    "tool": "add",
                    "args": {"a": 2, "b": 3},
                    "expression": "2 + 3",
                }
            ]
        )
        return AIMessage(content=content)


class _FakePlannerAndExecutorModel(Runnable):
    """Fake model used to test the full planner + executor flow.

    Call sequence:
    1. Planner: returns a JSON plan with a single add step.
    2. Executor/agent: first call -> tool call for add(2,3)
    3. Executor/agent: second call -> final natural-language answer using tool result.
    """

    def __init__(self) -> None:
        self._call_count = 0

    def invoke(self, input, config=None, **kwargs):
        from langchain_core.messages import AIMessage

        self._call_count += 1

        # Planner call: input is a list of messages
        if self._call_count == 1:
            content = json.dumps(
                [
                    {
                        "id": 1,
                        "description": "add 2 and 3",
                        "tool": "add",
                        "args": {"a": 2, "b": 3},
                        "expression": "2 + 3",
                    }
                ]
            )
            return AIMessage(content=content)

        # Executor calls: input is either list of messages or dict with "messages"
        messages = input if isinstance(input, (list, tuple)) else input.get("messages", [])
        # First executor call: return tool call
        if self._call_count == 2:
            return AIMessage(
                content="",
                tool_calls=[
                    {"id": "call-1", "name": "add", "args": json.dumps({"a": 2, "b": 3})},
                ],
            )

        # Second executor call: consume ToolMessage and produce final answer
        last = messages[-1]
        content = getattr(last, "content", None) or str(last)
        try:
            payload = json.loads(content)
            result = payload.get("result")
        except (json.JSONDecodeError, TypeError):
            result = None
        return AIMessage(content=f"The result is {result}.")


def test_plan_for_input_parses_tool_aware_steps():
    planner_llm = _FakePlannerModel()
    steps = plan_for_input("please add two numbers", planner_llm)

    assert len(steps) == 1
    step = steps[0]
    assert step["id"] == 1
    assert step["description"] == "add 2 and 3"
    assert step.get("tool") == "add"
    assert step.get("args") == {"a": 2, "b": 3}
    assert step.get("expression") == "2 + 3"


def test_agent_with_planning_outer_graph_flow():
    # Temporarily enable planning for this test
    old_enable_planning = settings.enable_planning
    settings.enable_planning = True
    try:
        agent = Agent(llm=_FakePlannerAndExecutorModel())
        state = agent.run("please add two numbers with planning")

        assert state.selected_tool == "add"
        assert state.tool_args == {"a": 2, "b": 3}
        assert state.tool_result == 5
        assert state.final_response == "The result is 5."
        # Ensure planning + execution trace entries exist
        assert any(step.step == "plan_created" for step in state.trace_steps)
        assert any(step.step == "tool_selected" for step in state.trace_steps)
        assert any(step.step == "tool_executed" for step in state.trace_steps)
        assert any(step.step == "final_response" for step in state.trace_steps)
    finally:
        settings.enable_planning = old_enable_planning

