"""Build and compile the LangGraph agent graph."""

from __future__ import annotations

from typing import Optional

from langchain_core.runnables import Runnable
from langgraph.graph import END, StateGraph

from agentic_app.config import settings
from agentic_app.graph.state import GraphState
from agentic_app.graph import nodes
from agentic_app.llm import get_llm


def build_executor_graph(llm: Optional[Runnable] = None):
    """Compile the inner ReAct executor graph (agent + tools + finalize)."""
    model = llm or get_llm()
    from agentic_app.tools.langchain_tools import get_langchain_tools

    tools = get_langchain_tools()
    llm_with_tools = model.bind_tools(tools)
    max_steps = settings.max_steps

    def agent(state: GraphState) -> GraphState:
        return nodes.agent_node(state, llm_with_tools)

    def finalize(state: GraphState) -> GraphState:
        return nodes.finalize_node(state)

    def route_after_agent(state: GraphState) -> str:
        steps = int(state.get("steps", 0) or 0)
        if nodes._has_tool_calls(state["messages"]) and steps < max_steps:
            return "tools"
        return "finalize"

    def route_after_tools(state: GraphState) -> str:
        if state.get("error"):
            return "finalize"
        return "agent"

    builder = StateGraph(GraphState)
    builder.add_node("agent", agent)
    builder.add_node("tools", nodes.tools_node)
    builder.add_node("finalize", finalize)
    builder.set_entry_point("agent")
    builder.add_conditional_edges("agent", route_after_agent, {"tools": "tools", "finalize": "finalize"})
    builder.add_conditional_edges("tools", route_after_tools, {"agent": "agent", "finalize": "finalize"})
    builder.add_edge("finalize", END)
    return builder.compile()


def build_graph(llm: Optional[Runnable] = None):
    """Compile the outer planner/executor/validator/replanner/finalize graph."""
    model = llm or get_llm()

    # Inner executor graph (ReAct loop) reused for each plan step.
    executor_graph = build_executor_graph(llm=model)

    def planner(state: GraphState) -> GraphState:
        return nodes.planner_node(state, model)

    def executor(state: GraphState) -> GraphState:
        return nodes.executor_node(state, executor_graph)

    def validator(state: GraphState) -> GraphState:
        return nodes.validator_node(state)

    def replanner(state: GraphState) -> GraphState:
        return nodes.replanner_node(state, model)

    def finalize(state: GraphState) -> GraphState:
        return nodes.finalize_node(state)

    def route_after_planner(state: GraphState) -> str:
        if state.get("error"):
            return "finalize"
        plan = state.get("plan") or []
        if plan:
            return "executor"
        return "finalize"

    def route_after_validator(state: GraphState) -> str:
        validation = state.get("validation_result") or {}
        status = validation.get("status") or "ok"
        plan = state.get("plan") or []
        index = int(state.get("current_step_index", 0) or 0)

        if status == "fatal":
            return "finalize"
        if status == "need_replan":
            return "replanner"
        if index < len(plan):
            return "executor"
        return "finalize"

    def route_after_replanner(state: GraphState) -> str:
        if state.get("error"):
            return "finalize"
        plan = state.get("plan") or []
        if plan:
            return "executor"
        return "finalize"

    builder = StateGraph(GraphState)
    builder.add_node("planner", planner)
    builder.add_node("executor", executor)
    builder.add_node("validator", validator)
    builder.add_node("replanner", replanner)
    builder.add_node("finalize", finalize)

    builder.set_entry_point("planner")
    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {"executor": "executor", "finalize": "finalize"},
    )
    builder.add_edge("executor", "validator")
    builder.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "executor": "executor",
            "replanner": "replanner",
            "finalize": "finalize",
        },
    )
    builder.add_conditional_edges(
        "replanner",
        route_after_replanner,
        {"executor": "executor", "finalize": "finalize"},
    )
    builder.add_edge("finalize", END)

    return builder.compile()
