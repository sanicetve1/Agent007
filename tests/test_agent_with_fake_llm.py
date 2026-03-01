from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from agentic_app.agent import Agent
from agentic_app.memory import InMemoryConversationStore, MemoryTurn


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


class FakeLLMClient:
    """Fake LLM that always calls the add tool with fixed arguments, then formats the result."""

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str | Dict[str, Any] | None = "auto",
    ) -> Any:
        if tools is not None:
            return _FakeMessage(
                content=None,
                tool_calls=[_FakeToolCall("add", {"a": 2, "b": 3})],
            )

        tool_msg = messages[-1]
        payload = json.loads(tool_msg["content"])
        result = payload["result"]
        return _FakeMessage(content=f"The result is {result}.")


class InspectingFakeLLMClient(FakeLLMClient):
    def __init__(self) -> None:
        self.first_turn_messages: Optional[List[Dict[str, Any]]] = None

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str | Dict[str, Any] | None = "auto",
    ) -> Any:
        if tools is not None:
            self.first_turn_messages = list(messages)
        return super().chat(messages=messages, tools=tools, tool_choice=tool_choice)


class DivideByZeroLLMClient:
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str | Dict[str, Any] | None = "auto",
    ) -> Any:
        if tools is not None:
            return _FakeMessage(
                content=None,
                tool_calls=[_FakeToolCall("divide", {"a": 1, "b": 0})],
            )
        return _FakeMessage(content="unused")


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


def test_agent_memory_load_and_save():
    llm = InspectingFakeLLMClient()
    memory = InMemoryConversationStore()
    session_id = "session-1"
    memory.append_turn(
        session_id,
        MemoryTurn(user_input="what is 1+1?", assistant_response="The result is 2."),
    )

    agent = Agent(llm_client=llm, memory_store=memory)
    state = agent.run("please add two numbers", session_id=session_id)

    assert state.final_response == "The result is 5."
    assert llm.first_turn_messages is not None

    roles = [msg["role"] for msg in llm.first_turn_messages]
    assert roles[:3] == ["system", "user", "assistant"]
    assert llm.first_turn_messages[1]["content"] == "what is 1+1?"
    assert llm.first_turn_messages[2]["content"] == "The result is 2."

    turns = memory.get_turns(session_id)
    assert len(turns) == 2
    assert turns[-1].user_input == "please add two numbers"
    assert turns[-1].assistant_response == "The result is 5."
    assert any(step.step == "memory_loaded" for step in state.trace_steps)
    assert any(step.step == "memory_saved" for step in state.trace_steps)


def test_agent_memory_session_isolation():
    llm = InspectingFakeLLMClient()
    memory = InMemoryConversationStore()
    memory.append_turn("session-a", MemoryTurn(user_input="a", assistant_response="A"))
    memory.append_turn("session-b", MemoryTurn(user_input="b", assistant_response="B"))

    agent = Agent(llm_client=llm, memory_store=memory)
    agent.run("new", session_id="session-a")

    assert llm.first_turn_messages is not None
    first_user = llm.first_turn_messages[1]
    first_assistant = llm.first_turn_messages[2]
    assert first_user["content"] == "a"
    assert first_assistant["content"] == "A"


def test_agent_memory_disabled_parity():
    llm = InspectingFakeLLMClient()
    agent = Agent(llm_client=llm)
    state = agent.run("please add two numbers", session_id="ignored")

    assert state.final_response == "The result is 5."
    assert llm.first_turn_messages is not None
    roles = [msg["role"] for msg in llm.first_turn_messages]
    assert roles == ["system", "user"]
    loaded = [s for s in state.trace_steps if s.step == "memory_loaded"]
    assert loaded and loaded[0].info["enabled"] is False


def test_agent_respects_history_turn_limit():
    llm = InspectingFakeLLMClient()
    memory = InMemoryConversationStore()
    for i in range(5):
        memory.append_turn(
            "session-1",
            MemoryTurn(user_input=f"u{i}", assistant_response=f"a{i}"),
        )

    agent = Agent(llm_client=llm, memory_store=memory, history_turn_limit=2)
    agent.run("current", session_id="session-1")

    assert llm.first_turn_messages is not None
    roles = [msg["role"] for msg in llm.first_turn_messages]
    assert roles == ["system", "user", "assistant", "user", "assistant", "user"]
    assert llm.first_turn_messages[1]["content"] == "u3"
    assert llm.first_turn_messages[3]["content"] == "u4"


def test_agent_saves_error_turn_to_memory():
    memory = InMemoryConversationStore()
    agent = Agent(llm_client=DivideByZeroLLMClient(), memory_store=memory)

    state = agent.run("divide 1 by 0", session_id="err-session")

    assert state.final_response is not None
    assert "Tool 'divide' failed" in state.final_response
    turns = memory.get_turns("err-session")
    assert len(turns) == 1
    assert turns[0].user_input == "divide 1 by 0"
    assert "Tool 'divide' failed" in turns[0].assistant_response


def test_agent_truncates_saved_memory_messages():
    memory = InMemoryConversationStore()
    agent = Agent(
        llm_client=FakeLLMClient(),
        memory_store=memory,
        memory_max_chars_per_message=10,
    )

    state = agent.run("please add two numbers with extra long text", session_id="truncate")

    assert state.final_response == "The result is 5."
    turns = memory.get_turns("truncate")
    assert len(turns) == 1
    assert len(turns[0].user_input) == 10
