from __future__ import annotations

from typing import Any, Dict

from agentic_app.tools.base import Tool


class DivideTool(Tool):
    name = "divide"
    description = "Divide one number by another, returning a float."
    input_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "a": {
                "type": "number",
                "description": "Dividend.",
            },
            "b": {
                "type": "number",
                "description": "Divisor. Must not be zero.",
            },
        },
        "required": ["a", "b"],
    }

    def run(self, *, a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Division by zero is not allowed.")
        return a / b

