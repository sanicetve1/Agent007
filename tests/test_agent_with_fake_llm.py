from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from agentic_app.agent import Agent
from agentic_app.llm.client import LLMClient


class _FakeMessage:
    def __init__(self, content: str | None = None, tool_calls: Optional[list[Any]] = None):
        self.content = content
        self.tool_calls = tool_calls or []


class _FakeToolCall:
    def __init__(self, tool_name: str, arguments: Dict[str, Any]):
        self.id = "call-1"
        self.type = "function"

        class Func:
            def __init__(self, name: str, arguments: Dict[str, Any]):
                self.name = name
                self.arguments = json.dumps(arguments)

        self.function = Func(tool_name, arguments)


class FakeLLMClient(LLMClient):
    """Fake LLM that always calls the add tool with fixed arguments, then formats the result."""

    def __init__(self) -> None:
        # Skip real parent init
        pass

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str | Dict[str, Any] | None = "auto",
    ) -> Any:
        # First turn: select tool
        if tools is not None:
            return _FakeMessage(
                content=None,
                tool_calls=[_FakeToolCall("add", {"a": 2, "b": 3})],
            )

        # Second turn: format final answer
        # Last message is the tool result content
        tool_msg = messages[-1]
        payload = json.loads(tool_msg["content"])
        result = payload["result"]
        return _FakeMessage(content=f"The result is {result}.")


def test_agent_with_fake_llm():
    agent = Agent(llm_client=FakeLLMClient())
    state = agent.run("please add two numbers")

    assert state.selected_tool == "add"
    assert state.tool_args == {"a": 2, "b": 3}
    assert state.tool_result == 5
    assert state.final_response == "The result is 5."
    assert any(step.step == "tool_selected" for step in state.trace_steps)
    assert any(step.step == "tool_executed" for step in state.trace_steps)
    assert any(step.step == "final_response" for step in state.trace_steps)

