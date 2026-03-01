from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class Tool(ABC):
    """Abstract interface that all tools must implement."""

    #: Machine-readable tool name used by the LLM.
    name: str
    #: Human-readable description of the tool.
    description: str
    #: JSON schema for tool arguments.
    input_schema: Dict[str, Any]

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:  # pragma: no cover - interface only
        """Execute the tool with keyword arguments."""
        raise NotImplementedError

