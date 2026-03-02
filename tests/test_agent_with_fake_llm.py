"""Agent orchestration test using a fake LangChain model."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

from agentic_app.agent import Agent


class _FakeLangChainModel(Runnable):
    """Fake model: first call returns add(2,3) tool call, second returns final text."""

    def __init__(self) -> None:
        self._call_count = 0

    def invoke(self, input, config=None, **kwargs):
        messages = input if isinstance(input, (list, tuple)) else input.get("messages", [])
        self._call_count += 1
        if self._call_count == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {"id": "call-1", "name": "add", "args": json.dumps({"a": 2, "b": 3})},
                ],
            )
        last = messages[-1]
        content = getattr(last, "content", None) or str(last)
        try:
            payload = json.loads(content)
            result = payload.get("result")
        except (json.JSONDecodeError, TypeError):
            result = None
        return AIMessage(content=f"The result is {result}.")


def test_agent_with_fake_llm():
    agent = Agent(llm=_FakeLangChainModel())
    state = agent.run("please add two numbers")

    assert state.selected_tool == "add"
    assert state.tool_args == {"a": 2, "b": 3}
    assert state.tool_result == 5
    assert state.final_response == "The result is 5."
    assert any(step.step == "tool_selected" for step in state.trace_steps)
    assert any(step.step == "tool_executed" for step in state.trace_steps)
    assert any(step.step == "final_response" for step in state.trace_steps)
