from __future__ import annotations

from typing import Optional

from agentic_app import app
from agentic_app.agent.state import AgentState


class _FakeAgent:
    def __init__(self) -> None:
        self.calls = []

    def run(self, user_input: str, session_id: Optional[str] = None) -> AgentState:
        self.calls.append((user_input, session_id))
        state = AgentState(user_input=user_input)
        state.final_response = "ok"
        return state


def test_repl_reset_clears_memory_without_agent_run(monkeypatch, capsys):
    fake_agent = _FakeAgent()

    monkeypatch.setattr(app.settings, "enable_memory", True)
    monkeypatch.setattr(app, "_build_agent", lambda memory_store=None: fake_agent)

    user_inputs = iter(["/reset", "exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(user_inputs))

    exit_code = app.repl()

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Memory is enabled for this REPL session" in out
    assert "Conversation memory cleared for this session." in out
    assert fake_agent.calls == []
