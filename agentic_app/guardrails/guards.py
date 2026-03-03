"""Minimal guard checks. Return (ok: bool, error_message: str | None)."""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Tuple


# Limits (domain-agnostic; tune per deployment)
MAX_INPUT_LEN = 4000
INPUT_FORBIDDEN_PATTERN = re.compile(r"(?i)(ignore\s+previous|system\s*:\s*you\s+are)")
OUTPUT_FORBIDDEN_PATTERN = re.compile(r"(?i)(ignore\s+previous|system\s*:\s*you\s+are)")
NUMERIC_ABS_MAX = 1e15


def input_guard(text: str) -> Tuple[bool, str | None]:
    """Validate user input: length and simple prompt-injection heuristics."""
    if not isinstance(text, str):
        return False, "Input must be a string."
    if len(text.strip()) == 0:
        return False, "Input cannot be empty."
    if len(text) > MAX_INPUT_LEN:
        return False, f"Input exceeds maximum length ({MAX_INPUT_LEN} characters)."
    if INPUT_FORBIDDEN_PATTERN.search(text):
        return False, "Input contains disallowed content."
    return True, None


def tool_guard(tool_name: str, args: Dict[str, Any]) -> Tuple[bool, str | None]:
    """Validate tool arguments: types and numeric ranges."""
    if not isinstance(args, dict):
        return False, "Tool arguments must be a dict."
    for k, v in args.items():
        if isinstance(v, (int, float)):
            if not math.isfinite(v):
                return False, f"Argument '{k}' must be finite."
            if abs(v) > NUMERIC_ABS_MAX:
                return False, f"Argument '{k}' exceeds allowed magnitude."
    return True, None


def output_guard(final_text: str, system_prompt_snippet: str = "") -> Tuple[bool, str | None]:
    """Post-check final answer: no obvious prompt leak or forbidden content."""
    if not isinstance(final_text, str):
        return False, "Output must be a string."
    if system_prompt_snippet and system_prompt_snippet.strip() in final_text:
        return False, "Output must not repeat system instructions."
    if OUTPUT_FORBIDDEN_PATTERN.search(final_text):
        return False, "Output contains disallowed content."
    return True, None
