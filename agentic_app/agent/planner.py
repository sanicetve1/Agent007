from __future__ import annotations

from typing import Any, Dict, List, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable


PLANNER_SYSTEM_PROMPT = """
You are a planning agent for a math tool-using assistant.

Given a single user request, break it into a SMALL sequence of clear, ordered steps.
Each step should ideally map to a single arithmetic tool call (add, subtract, multiply, divide),
but the executor can still infer tools from the natural-language description.

Return ONLY JSON in this shape:

[
  {
    "id": 1,
    "description": "add 5 and 5",
    "tool": "add",
    "args": {"a": 5, "b": 5},
    "expression": "5 + 5"
  },
  {
    "id": 2,
    "description": "multiply the result by 2",
    "tool": "multiply",
    "args": {"a": "result", "b": 2},
    "expression": "result * 2"
  }
]

Rules:
- Keep the number of steps as small as possible.
- Each step MUST have a non-empty description.
- 'tool' and 'args' are helpful but OPTIONAL; if omitted, the executor will infer the tool.
- 'expression' is OPTIONAL, useful for pure math expressions.
""".strip()


class PlanStep(TypedDict, total=False):
    """Single planning step for the outer planner/executor graph.

    Fields are intentionally flexible so the planner can return
    either minimal (description-only) or tool-aware steps.
    """

    id: int
    description: str
    tool: str | None
    args: Dict[str, Any] | None
    expression: str | None


def plan_for_input(user_input: str, llm: Runnable) -> List[PlanStep]:
    """Call the planning LLM and parse a list of plan steps.

    The parser is intentionally tolerant of partial / slightly malformed
    outputs: it accepts both the new tool-aware schema and the older
    `{description, expression}`-only shape.
    """
    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=user_input),
    ]
    msg = llm.invoke(messages)
    import json

    try:
        data = json.loads(getattr(msg, "content", "") or "[]")
    except json.JSONDecodeError:
        return []

    steps: List[PlanStep] = []
    if not isinstance(data, list):
        return steps

    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue
        desc = str(item.get("description") or "").strip()
        if not desc:
            continue

        # Accept both new and legacy shapes
        raw_id = item.get("id")
        try:
            step_id = int(raw_id) if raw_id is not None else idx
        except (TypeError, ValueError):
            step_id = idx

        tool = item.get("tool")
        tool_str = str(tool).strip() if isinstance(tool, str) else ""
        args = item.get("args")
        args_dict: Dict[str, Any] | None
        if isinstance(args, dict):
            args_dict = args
        else:
            args_dict = None

        expr_raw = item.get("expression")
        expr_str = str(expr_raw).strip() if expr_raw is not None else ""

        step: PlanStep = {
            "id": step_id,
            "description": desc,
        }
        if tool_str:
            step["tool"] = tool_str
        if args_dict is not None:
            step["args"] = args_dict
        if expr_str:
            step["expression"] = expr_str

        steps.append(step)

    return steps

