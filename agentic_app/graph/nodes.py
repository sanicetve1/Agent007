"""LangGraph nodes: agent (LLM) and tools (execute)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.runnables import Runnable

from agentic_app.graph.state import GraphState
from agentic_app.tools import get_tool, get_openai_tool_specs


def _is_tool_message(msg: BaseMessage) -> bool:
    return isinstance(msg, ToolMessage)


def _has_tool_calls(messages: Sequence[BaseMessage]) -> bool:
    if not messages:
        return False
    last = messages[-1]
    return bool(getattr(last, "tool_calls", None))


def agent_node(
    state: GraphState,
    llm_with_tools: Runnable,
) -> GraphState:
    """Reasoning + decision node.

    - Always calls the tool-enabled LLM with the full message history.
    - Increments the reasoning step counter.
    - Emits trace entries for tools availability and tool selection
      (or direct answer when no tool is used).
    - Does NOT finalize; the graph decides when to stop.
    """
    messages = state["messages"]
    trace_delta: List[Dict[str, Any]] = []

    # Bounded reasoning loop counter
    current_steps = int(state.get("steps", 0) or 0)
    new_steps = current_steps + 1

    tool_names = [s["function"]["name"] for s in get_openai_tool_specs()]
    trace_delta.append({"step": "tools_available", "info": {"tools": tool_names}})

    response = llm_with_tools.invoke(messages)
    out_messages: List[BaseMessage] = [response]

    tool_calls = getattr(response, "tool_calls", None)
    if tool_calls:
        tc = tool_calls[0]
        name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
        args_raw = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", "{}")
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
        except (json.JSONDecodeError, TypeError):
            args = {}
        trace_delta.append(
            {
                "step": "tool_selected",
                "info": {"tool_name": name, "tool_args": args},
            }
        )
    else:
        content = getattr(response, "content", "") or ""
        trace_delta.append({"step": "no_tool_used", "info": {"response": content}})

    return {"messages": out_messages, "trace": trace_delta, "steps": new_steps}


def tools_node(state: GraphState) -> GraphState:
    """Execute tool calls from the last AIMessage and append ToolMessages."""
    messages = state["messages"]
    last = messages[-1]
    tool_calls = getattr(last, "tool_calls", None) or []
    if not tool_calls:
        # No new trace here; just return empty updates so previous
        # trace is preserved as-is by the reducer.
        return {}

    tool_messages: List[ToolMessage] = []
    last_tool_name: Optional[str] = None
    last_tool_args: Dict[str, Any] = {}
    last_tool_result: Any = None
    error: Optional[str] = None
    trace_delta: List[Dict[str, Any]] = []

    for tc in tool_calls:
        tid = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", "") or ""
        name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
        raw_args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", "{}") or "{}"
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except (json.JSONDecodeError, TypeError):
            args = {}
        try:
            tool = get_tool(name)
            result = tool.run(**args)
            last_tool_name = name
            last_tool_args = args
            last_tool_result = result
            tool_messages.append(
                ToolMessage(tool_call_id=tid, content=json.dumps({"result": result}))
            )
            trace_delta.append(
                {
                    "step": "tool_executed",
                    "info": {
                        "tool_name": name,
                        "tool_args": args,
                        "tool_result": result,
                    },
                }
            )
        except Exception as exc:
            error = f"Tool '{name}' failed: {exc}"
            trace_delta.append({"step": "tool_error", "info": {"error": str(exc)}})
            tool_messages.append(ToolMessage(tool_call_id=tid, content=json.dumps({"error": str(exc)})))
            break

    return {
        "messages": tool_messages,
        "trace": trace_delta,
        "last_tool_name": last_tool_name,
        "last_tool_args": last_tool_args,
        "last_tool_result": last_tool_result,
        "error": error,
    }


def finalize_node(state: GraphState) -> GraphState:
    """Finalize node: produce final response trace entry.

    This node does not call the LLM. It assumes the last assistant
    message already contains the final natural-language answer when
    no more tools are requested, or that an error has been set in state.
    """
    messages = state.get("messages") or []
    trace_delta: List[Dict[str, Any]] = []

    if state.get("error"):
        final = state["error"]
    elif messages:
        last = messages[-1]
        final = getattr(last, "content", "") or ""
    else:
        final = ""

    trace_delta.append({"step": "final_response", "info": {"response": final}})
    return {"trace": trace_delta}
