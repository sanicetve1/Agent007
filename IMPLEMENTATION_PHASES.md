# Stateful Agent Upgrade Progress

This checklist tracks the phased migration from stateless-only behavior to stateless-core with optional stateful context.

## Phase 0: Baseline freeze
- Completed: existing orchestration and tool execution flow kept intact.

## Phase 1: Memory foundation
- Completed: `MemoryStore` interface and `InMemoryConversationStore` implementation added.

## Phase 2: Non-breaking agent integration
- Completed: memory injected into `Agent` as an optional dependency.
- Completed: `session_id` support in `Agent.run(...)`.
- Completed: memory load before first LLM call and save after terminal outcomes.

## Phase 3: CLI session wiring
- Completed: REPL uses one stable session id when memory is enabled.
- Completed: one-shot path remains stateless by default.

## Phase 4: Config-driven rollout
- Completed: memory remains behind `ENABLE_MEMORY`.
- Completed: memory behavior documented in README.
- Completed: memory limits configurable via `MEMORY_TURN_LIMIT` and `MEMORY_MAX_CHARS_PER_MESSAGE`.

## Phase 5: Test hardening
- Completed: tests for parity when memory is disabled.
- Completed: tests for memory load/save, session isolation, turn-limit behavior, and error-path persistence.

## Phase 6: Operational guardrails
- Completed: bounded history loading.
- Completed: truncation guardrail for persisted and replayed memory text.
- Completed: session reset command in REPL (`/reset`).

## Phase 7: Checkpoint and release safety
- Completed: explicit phase checklist committed.
- Completed: full test suite passing in local environment with `PYTHONPATH=. pytest -q`.
