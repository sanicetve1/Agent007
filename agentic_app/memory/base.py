from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class MemoryTurn:
    user_input: str
    assistant_response: str


class MemoryStore(ABC):
    """Abstract interface for conversation memory providers."""

    @abstractmethod
    def get_turns(self, session_id: str) -> List[MemoryTurn]:
        """Return ordered conversation turns for a session."""
        raise NotImplementedError

    @abstractmethod
    def append_turn(self, session_id: str, turn: MemoryTurn) -> None:
        """Append a conversation turn to a session."""
        raise NotImplementedError

    @abstractmethod
    def clear_session(self, session_id: str) -> None:
        """Remove all turns for a session."""
        raise NotImplementedError
