from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from agentic_app.agent.prompt import SYSTEM_PROMPT
from agentic_app.agent.state import AgentState
from agentic_app.llm import LLMClient
from agentic_app.memory import MemoryStore, MemoryTurn
from agentic_app.tools import get_tool, get_openai_tool_specs


class Agent:
    """Core agent loop that routes user input through the LLM and tools."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        memory_store: Optional[MemoryStore] = None,
        history_turn_limit: int = 6,
    ) -> None:
        self._llm = llm_client or LLMClient()
        self._memory_store = memory_store
        self._history_turn_limit = max(0, int(history_turn_limit))

    def _build_memory_messages(self, session_id: Optional[str]) -> List[Dict[str, Any]]:
        if not self._memory_store or not session_id:
            return []

        turns = self._memory_store.get_turns(session_id)
        if self._history_turn_limit:
            turns = turns[-self._history_turn_limit :]

        messages: List[Dict[str, Any]] = []
        for turn in turns:
            messages.append({"role": "user", "content": turn.user_input})
            messages.append({"role": "assistant", "content": turn.assistant_response})
        return messages

    def run(self, user_input: str, session_id: Optional[str] = None) -> AgentState:
        state = AgentState(user_input=user_input)
        state.add_step("received_input", user_input=user_input)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        memory_messages = self._build_memory_messages(session_id)
        if memory_messages:
            messages.extend(memory_messages)
        state.add_step(
            "memory_loaded",
            enabled=bool(self._memory_store and session_id),
            session_id=session_id,
            turns_loaded=len(memory_messages) // 2,
        )

        messages.append({"role": "user", "content": user_input})

        tools = get_openai_tool_specs()
        state.add_step(
            "tools_available",
            tools=[spec["function"]["name"] for spec in tools],
        )

        # Ask the LLM to choose a tool and arguments.
        message = self._llm.chat(messages=messages, tools=tools, tool_choice="auto")

        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            # No tool call requested; treat as a direct answer.
            content = message.content or ""
            state.final_response = content
            state.add_step("no_tool_used", response=content)
            self._save_turn(session_id, user_input, content, state)
            return state

        tool_call = tool_calls[0]
        tool_name = tool_call.function.name
        raw_arguments = tool_call.function.arguments or "{}"

        try:
            tool_args: Dict[str, Any] = json.loads(raw_arguments)
        except json.JSONDecodeError:
            tool_args = {}

        state.selected_tool = tool_name
        state.tool_args = tool_args
        state.add_step(
            "tool_selected",
            tool_name=tool_name,
            tool_args=tool_args,
        )

        # Execute the tool.
        tool = get_tool(tool_name)
        try:
            result = tool.run(**tool_args)
        except Exception as exc:
            state.tool_result = None
            state.add_step("tool_error", error=str(exc))
            state.final_response = f"Tool '{tool_name}' failed: {exc}"
            self._save_turn(session_id, user_input, state.final_response, state)
            return state

        state.tool_result = result
        state.add_step(
            "tool_executed",
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=result,
        )

        # Ask the LLM to format the final answer using the result.
        followup_messages: List[Dict[str, Any]] = [
            *messages,
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(tool_args),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": json.dumps({"result": result}),
            },
        ]

        final_message = self._llm.chat(
            messages=followup_messages, tools=None, tool_choice=None
        )
        final_content = final_message.content or ""

        state.final_response = final_content
        state.add_step("final_response", response=final_content)
        self._save_turn(session_id, user_input, final_content, state)

        return state

    def _save_turn(
        self,
        session_id: Optional[str],
        user_input: str,
        assistant_response: str,
        state: AgentState,
    ) -> None:
        if not self._memory_store or not session_id:
            state.add_step(
                "memory_saved",
                enabled=False,
                session_id=session_id,
            )
            return

        self._memory_store.append_turn(
            session_id,
            MemoryTurn(user_input=user_input, assistant_response=assistant_response),
        )
        state.add_step(
            "memory_saved",
            enabled=True,
            session_id=session_id,
        )
