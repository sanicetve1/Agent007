"""LangChain tool adapters from the registry for use in the graph (bind_tools, etc.)."""

from __future__ import annotations

from typing import List

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agentic_app.tools import get_tool, list_tools


class _TwoNumbers(BaseModel):
    a: float = Field(description="First number.")
    b: float = Field(description="Second number.")


def get_langchain_tools() -> List[StructuredTool]:
    """Return LangChain StructuredTools wrapping the registered tools."""
    result: List[StructuredTool] = []
    for t in list_tools():
        result.append(
            StructuredTool.from_function(
                name=t.name,
                description=t.description,
                func=(lambda _t: lambda **kw: _t.run(**kw))(t),
                args_schema=_TwoNumbers,
            )
        )
    return result
