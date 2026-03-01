from __future__ import annotations

from typing import Any, Dict, List

from agentic_app.tools.base import Tool


_TOOL_REGISTRY: Dict[str, Tool] = {}


def register_tool(tool: Tool) -> None:
    """Register a tool instance under its name."""
    _TOOL_REGISTRY[tool.name] = tool


def get_tool(name: str) -> Tool:
    """Retrieve a registered tool by name."""
    if name not in _TOOL_REGISTRY:
        available = ", ".join(sorted(_TOOL_REGISTRY)) or "<none>"
        raise KeyError(f"Unknown tool '{name}'. Available tools: {available}")
    return _TOOL_REGISTRY[name]


def list_tools() -> List[Tool]:
    """Return all registered tools."""
    return list(_TOOL_REGISTRY.values())


def get_openai_tool_specs() -> List[Dict[str, Any]]:
    """Return OpenAI tool definitions for all registered tools."""
    specs: List[Dict[str, Any]] = []
    for tool in list_tools():
        specs.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
        )
    return specs

