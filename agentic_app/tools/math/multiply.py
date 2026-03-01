from __future__ import annotations

from typing import Any, Dict

from agentic_app.tools.base import Tool


class MultiplyTool(Tool):
    name = "multiply"
    description = "Multiply two numbers."
    input_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "a": {
                "type": "number",
                "description": "First factor.",
            },
            "b": {
                "type": "number",
                "description": "Second factor.",
            },
        },
        "required": ["a", "b"],
    }

    def run(self, *, a: float, b: float) -> float:
        return a * b

