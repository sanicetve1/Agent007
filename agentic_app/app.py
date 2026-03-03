from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from agentic_app.agent import Agent
from agentic_app.agent.state import AgentState, TraceStep
from agentic_app.config import settings
from agentic_app.memory import ConversationMemory


def _format_trace_step(step: TraceStep) -> dict[str, Any]:
    return {
        "step": step.step,
        "info": step.info,
    }


def run_once(text: str) -> int:
    agent = Agent(memory=None)
    state: AgentState = agent.run(text)

    trace_payload = [_format_trace_step(s) for s in state.trace_steps]
    print("=== Execution Trace ===")
    print(json.dumps(trace_payload, indent=2))
    print()
    print("=== Final Answer ===")
    print(state.final_response or "")

    return 0


def repl() -> int:
    memory = ConversationMemory(max_messages=settings.max_memory_messages) if settings.enable_memory else None
    agent = Agent(memory=memory)
    print("Agentic Math CLI. Type 'exit' or Ctrl+C to quit.")
    while True:
        try:
            text = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            break

        state = agent.run(text)
        trace_payload = [_format_trace_step(s) for s in state.trace_steps]
        print("=== Execution Trace ===")
        print(json.dumps(trace_payload, indent=2))
        print("=== Final Answer ===")
        print(state.final_response or "")
        print()

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Minimal agentic math CLI powered by an LLM."
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="Single instruction to run. If omitted, starts an interactive REPL.",
    )

    args = parser.parse_args(argv)
    if args.text:
        return run_once(args.text)
    return repl()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

