"""Build and compile the LangGraph agent graph."""

from __future__ import annotations

from typing import Optional

from langchain_core.runnables import Runnable
from langgraph.graph import END, StateGraph

from agentic_app.graph.state import GraphState
from agentic_app.graph import nodes
from agentic_app.llm import get_llm

MAX_STEPS = 4


def build_graph(llm: Optional[Runnable] = None):
    """Compile the agent graph. Optionally inject llm for tests."""
    model = llm or get_llm()
    from agentic_app.tools.langchain_tools import get_langchain_tools

    tools = get_langchain_tools()
    llm_with_tools = model.bind_tools(tools)

    def agent(state: GraphState) -> GraphState:
        return nodes.agent_node(state, llm_with_tools)

    def finalize(state: GraphState) -> GraphState:
        return nodes.finalize_node(state)

    def route_after_agent(state: GraphState) -> str:
        steps = int(state.get("steps", 0) or 0)
        if nodes._has_tool_calls(state["messages"]) and steps < MAX_STEPS:
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
