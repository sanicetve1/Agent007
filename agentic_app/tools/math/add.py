from __future__ import annotations

from typing import Any, Dict

from agentic_app.tools.base import Tool


class AddTool(Tool):
    name = "add"
    description = "Add two numbers together."
    input_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "a": {
                "type": "number",
                "description": "First addend.",
            },
            "b": {
                "type": "number",
                "description": "Second addend.",
            },
        },
        "required": ["a", "b"],
    }

    def run(self, *, a: float, b: float) -> float:
        return a + b

