from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


ToolFn = Callable[..., Dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]
    fn: ToolFn


_REGISTRY: Dict[str, ToolSpec] = {}


def register_tool(spec: ToolSpec) -> None:
    _REGISTRY[spec.name] = spec


def get_tool(name: str) -> ToolSpec:
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY)) or "<none>"
        raise KeyError(f"Unknown tool '{name}'. Available: {available}")
    return _REGISTRY[name]


def list_tools() -> list[ToolSpec]:
    return list(_REGISTRY.values())


def to_openai_function_tools() -> list[dict[str, Any]]:
    """
    Return OpenAI-style function tool descriptors for SDK wiring.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema,
            },
        }
        for t in list_tools()
    ]


def execute_tool(name: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Execute a registered tool by name with keyword args.
    """
    return get_tool(name).fn(**kwargs)

