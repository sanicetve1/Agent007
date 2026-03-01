from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from agentic_app.agent import Agent
from agentic_app.memory import InMemoryConversationStore


@dataclass
class _FakeToolFunction:
    name: str
    arguments: str


@dataclass
class _FakeToolCall:
    id: str
    type: str
    function: _FakeToolFunction


@dataclass
class _FakeMessage:
    content: Optional[str] = None
    tool_calls: Optional[list[Any]] = None


class TwoTurnMemoryFakeLLM:
    """Deterministic fake LLM to validate two-turn memory-driven behavior."""

    def __init__(self) -> None:
        self._call_index = 0

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str | Dict[str, Any] | None = "auto",
    ) -> Any:
        self._call_index += 1

        # turn 1 - choose add
        if self._call_index == 1 and tools is not None:
            return _FakeMessage(
                tool_calls=[
                    _FakeToolCall(
                        id="call-1",
                        type="function",
                        function=_FakeToolFunction(
                            name="add", arguments=json.dumps({"a": 2, "b": 2})
                        ),
                    )
                ]
            )

        # turn 1 - final answer
        if self._call_index == 2 and tools is None:
            payload = json.loads(messages[-1]["content"])
            return _FakeMessage(content=f"The result is {payload['result']}.")

        # turn 2 - choose multiply using remembered numbers
        if self._call_index == 3 and tools is not None:
            return _FakeMessage(
                tool_calls=[
                    _FakeToolCall(
                        id="call-2",
                        type="function",
                        function=_FakeToolFunction(
                            name="multiply", arguments=json.dumps({"a": 2, "b": 2})
                        ),
                    )
                ]
            )

        # turn 2 - final answer
        payload = json.loads(messages[-1]["content"])
        return _FakeMessage(content=f"The result is {payload['result']}.")


def test_memory_two_turn_sequence_2_plus_2_then_multiply_same_numbers():
    llm = TwoTurnMemoryFakeLLM()
    memory = InMemoryConversationStore()
    agent = Agent(llm_client=llm, memory_store=memory)

    session_id = "cli-seq"

    first = agent.run("2+2", session_id=session_id)
    second = agent.run("now multiply the same numbers", session_id=session_id)

    assert first.tool_result == 4
    assert first.final_response == "The result is 4."
    assert second.tool_result == 4
    assert second.final_response == "The result is 4."

    turns = memory.get_turns(session_id)
    assert len(turns) == 2
    assert turns[0].user_input == "2+2"
    assert turns[1].user_input == "now multiply the same numbers"
