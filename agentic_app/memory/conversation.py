from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, List

from agentic_app.memory.base import MemoryStore, MemoryTurn


class InMemoryConversationStore(MemoryStore):
    """Simple in-process memory store keyed by session id."""

    def __init__(self) -> None:
        self._sessions: DefaultDict[str, List[MemoryTurn]] = defaultdict(list)

    def get_turns(self, session_id: str) -> List[MemoryTurn]:
        return list(self._sessions.get(session_id, []))

    def append_turn(self, session_id: str, turn: MemoryTurn) -> None:
        self._sessions[session_id].append(turn)

    def clear_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]
