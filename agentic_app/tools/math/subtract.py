from __future__ import annotations

from typing import Any, Dict

from agentic_app.tools.base import Tool


class SubtractTool(Tool):
    name = "subtract"
    description = "Subtract one number from another."
    input_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "a": {
                "type": "number",
                "description": "Minuend.",
            },
            "b": {
                "type": "number",
                "description": "Subtrahend.",
            },
        },
        "required": ["a", "b"],
    }

    def run(self, *, a: float, b: float) -> float:
        return a - b

