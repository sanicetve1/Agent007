"""LangGraph nodes: agent (LLM) and tools (execute)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import Runnable

from agentic_app.agent.planner import PlanStep, plan_for_input
from agentic_app.agent.prompt import SYSTEM_PROMPT
from agentic_app.config import settings
from agentic_app.graph.state import GraphState
from agentic_app.guardrails import output_guard, tool_guard
from agentic_app.tools import get_tool, get_openai_tool_specs


def _is_tool_message(msg: BaseMessage) -> bool:
    return isinstance(msg, ToolMessage)


def _has_tool_calls(messages: Sequence[BaseMessage]) -> bool:
    if not messages:
        return False
    last = messages[-1]
    return bool(getattr(last, "tool_calls", None))


def planner_node(state: GraphState, llm: Runnable) -> GraphState:
    """Planner node: create a structured plan from the latest user request."""
    messages = state.get("messages") or []
    latest_user: Optional[HumanMessage] = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            latest_user = msg
            break

    user_text = getattr(latest_user, "content", "") if latest_user is not None else ""
    trace_delta: List[Dict[str, Any]] = []

    if not user_text:
        error = "Planning failed: no user input found."
        trace_delta.append({"step": "plan_error", "info": {"error": error}})
        return {"trace": trace_delta, "plan_status": "failed", "error": error}

    steps: List[PlanStep] = plan_for_input(user_text, llm)
    if not steps:
        error = "Planning failed: planner returned an empty plan."
        trace_delta.append({"step": "plan_error", "info": {"error": error}})
        return {"trace": trace_delta, "plan_status": "failed", "error": error}

    trace_delta.append(
        {
            "step": "plan_created",
            "info": {
                "steps": steps,
            },
        }
    )

    return {
        "trace": trace_delta,
        "plan": steps,
        "current_step_index": 0,
        "plan_status": "planned",
    }


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
        if settings.enable_guards:
            ok, err = tool_guard(name, args)
            if not ok:
                error = err or f"Tool '{name}' arguments rejected by guard."
                trace_delta.append({"step": "tool_error", "info": {"error": error}})
                tool_messages.append(ToolMessage(tool_call_id=tid, content=json.dumps({"error": error})))
                break
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


def executor_node(state: GraphState, executor_graph: Runnable) -> GraphState:
    """Executor node: run a single planned step via the inner ReAct graph."""
    plan = state.get("plan") or []
    index = int(state.get("current_step_index", 0) or 0)
    if not plan or index >= len(plan):
        # Nothing to do – no remaining steps.
        return {}

    step: PlanStep = plan[index]
    description = str(step.get("description") or "").strip()
    expression = str(step.get("expression") or "").strip()
    step_tool = str(step.get("tool") or "").strip()
    raw_args = step.get("args") or {}

    # Resolve any "result" placeholders in planner-provided args using the
    # previous step's numeric result so the executor has concrete arguments.
    resolved_args: Dict[str, Any] = {}
    incoming_last_result = state.get("last_tool_result")
    if isinstance(raw_args, dict):
        for k, v in raw_args.items():
            if isinstance(v, str) and v == "result":
                resolved_args[k] = incoming_last_result
            else:
                resolved_args[k] = v

    # Default instruction text, enriched with explicit tool/args when available.
    if description:
        base_instruction = description
    elif expression:
        base_instruction = expression
    else:
        base_instruction = "Execute the next planned step."

    if step_tool and resolved_args:
        # Make the tool and its concrete arguments explicit in the prompt so
        # the inner ReAct executor can deterministically pick the right tool
        # and argument values.
        args_str = ", ".join(f"{k}={resolved_args[k]!r}" for k in resolved_args)
        user_input = (
            f"{base_instruction} "
            f"Use the '{step_tool}' tool with arguments: {args_str}."
        )
    else:
        user_input = base_instruction

    from langchain_core.messages import SystemMessage

    system = SystemMessage(content=SYSTEM_PROMPT)
    current = HumanMessage(content=user_input)
    initial_messages: List[BaseMessage] = [system, current]

    initial_state: Dict[str, Any] = {
        "messages": initial_messages,
        "trace": [
            {
                "step": "plan_step_started",
                "info": {
                    "plan_step": index,
                    "plan_description": description,
                },
            }
        ],
        "steps": 0,
    }

    result = executor_graph.invoke(initial_state)

    raw_trace = result.get("trace") or []
    wrapped_trace: List[Dict[str, Any]] = []
    for t in raw_trace:
        info = dict(t.get("info") or {})
        info.setdefault("plan_step", index)
        info.setdefault("plan_description", description)
        wrapped_trace.append({"step": t.get("step", ""), "info": info})

    next_index = index + 1
    plan_status = "executing" if next_index < len(plan) else "done"

    return {
        "messages": result.get("messages") or [],
        "trace": wrapped_trace,
        "last_tool_name": result.get("last_tool_name"),
        "last_tool_args": result.get("last_tool_args") or {},
        "last_tool_result": result.get("last_tool_result"),
        "error": result.get("error"),
        "current_step_index": next_index,
        "plan_status": plan_status,
    }


def validator_node(state: GraphState) -> GraphState:
    """Validator node: lightweight sanity checks on the latest tool result / state."""
    error = state.get("error")
    if error:
        status = "fatal"
        reason = str(error)
    else:
        status = "ok"
        reason = "step_ok"

    validation_result: Dict[str, Any] = {"status": status, "reason": reason}
    trace_delta = [{"step": "validation_performed", "info": validation_result}]
    return {"validation_result": validation_result, "trace": trace_delta}


def replanner_node(state: GraphState, llm: Runnable) -> GraphState:
    """Replanner node: repair or extend the plan based on validation_result and history."""
    validation = state.get("validation_result") or {}
    reason = str(validation.get("reason") or "")

    messages = state.get("messages") or []
    original_user: Optional[HumanMessage] = None
    for msg in messages:
        if isinstance(msg, HumanMessage):
            original_user = msg
            break

    base_request = getattr(original_user, "content", "") if original_user is not None else ""
    if not base_request:
        error = "Replanning failed: original user input not available."
        trace_delta = [{"step": "plan_replan_failed", "info": {"error": error}}]
        return {
            "trace": trace_delta,
            "plan_status": "failed",
            "replan_reason": reason,
            "error": error,
        }

    if reason:
        replanning_input = (
            f"{base_request}\n\nThe previous plan failed for this reason: {reason}.\n"
            "Please propose a corrected plan starting from the current point."
        )
    else:
        replanning_input = base_request

    new_steps = plan_for_input(replanning_input, llm)
    trace_delta: List[Dict[str, Any]] = []

    if not new_steps:
        error = "Replanning failed: replanner returned an empty plan."
        trace_delta.append({"step": "plan_replan_failed", "info": {"error": error}})
        return {
            "trace": trace_delta,
            "plan_status": "failed",
            "replan_reason": reason,
            "error": error,
        }

    trace_delta.append(
        {
            "step": "plan_revised",
            "info": {
                "steps": new_steps,
                "reason": reason,
            },
        }
    )

    return {
        "trace": trace_delta,
        "plan": new_steps,
        "current_step_index": 0,
        "plan_status": "planned",
        "replan_reason": reason,
    }


def finalize_node(state: GraphState) -> GraphState:
    """Finalize node: produce final response trace entry.

    This node does not call the LLM. It assumes the last assistant
    message already contains the final natural-language answer when
    no more tools are requested, or that an error has been set in state.
    Optionally runs output guard and replaces with safe message on failure.
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

    if settings.enable_guards and final:
        ok, err = output_guard(final, system_prompt_snippet="You are a minimal math assistant")
        if not ok:
            final = "I cannot display that response due to a safety check."

    trace_delta.append({"step": "final_response", "info": {"response": final}})
    return {"trace": trace_delta}
