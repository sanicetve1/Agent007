from __future__ import annotations

import argparse
import json
import uuid
from typing import Any

from agentic_app.agent import Agent
from agentic_app.agent.state import AgentState, TraceStep
from agentic_app.config import settings
from agentic_app.memory import InMemoryConversationStore, MemoryStore


def _format_trace_step(step: TraceStep) -> dict[str, Any]:
    return {
        "step": step.step,
        "info": step.info,
    }


def _build_agent(memory_store: MemoryStore | None = None) -> Agent:
    if settings.enable_memory:
        return Agent(memory_store=memory_store or InMemoryConversationStore())
    return Agent()


def run_once(text: str) -> int:
    agent = _build_agent()
    state: AgentState = agent.run(text)

    trace_payload = [_format_trace_step(s) for s in state.trace_steps]
    print("=== Execution Trace ===")
    print(json.dumps(trace_payload, indent=2))
    print()
    print("=== Final Answer ===")
    print(state.final_response or "")

    return 0


def repl() -> int:
    memory_store = InMemoryConversationStore() if settings.enable_memory else None
    agent = _build_agent(memory_store=memory_store)
    session_id = str(uuid.uuid4()) if settings.enable_memory else None
    print("Agentic Math CLI. Type 'exit' or Ctrl+C to quit.")
    if settings.enable_memory:
        print("Memory is enabled for this REPL session. Type '/reset' to clear context.")

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

        if text.lower() == "/reset":
            if memory_store and session_id:
                memory_store.clear_session(session_id)
                print("Conversation memory cleared for this session.")
            else:
                print("Memory is not enabled.")
            continue

        state = agent.run(text, session_id=session_id)
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
