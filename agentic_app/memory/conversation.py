"""In-memory conversation history. Interface is stable for future DB-backed implementations."""

from __future__ import annotations

from typing import List, Optional

from langchain_core.messages import BaseMessage


class ConversationMemory:
    """Stores messages across turns. Replace with DB-backed implementation later without changing callers."""

    def __init__(self, max_messages: int = 50) -> None:
        self._max_messages = max(max_messages, 1)
        self._messages: List[BaseMessage] = []

    def get_messages(self) -> List[BaseMessage]:
        """Return recent messages (oldest first), trimmed to max_messages."""
        return list(self._messages[-self._max_messages :])

    def append(self, messages: List[BaseMessage]) -> None:
        """Append new messages and trim to max_messages."""
        self._messages.extend(messages)
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages :]

    def clear(self) -> None:
        """Clear all stored messages."""
        self._messages.clear()
