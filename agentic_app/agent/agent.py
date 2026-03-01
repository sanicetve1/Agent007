from __future__ import annotations

import json
from typing import Any, Dict, List

from agentic_app.agent.prompt import SYSTEM_PROMPT
from agentic_app.agent.state import AgentState
from agentic_app.llm import LLMClient
from agentic_app.tools import get_tool, get_openai_tool_specs


class Agent:
    """Core agent loop that routes user input through the LLM and tools."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client or LLMClient()

    def run(self, user_input: str) -> AgentState:
        state = AgentState(user_input=user_input)
        state.add_step("received_input", user_input=user_input)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]

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
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
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

        final_message = self._llm.chat(messages=followup_messages, tools=None, tool_choice=None)
        final_content = final_message.content or ""

        state.final_response = final_content
        state.add_step("final_response", response=final_content)

        return state

