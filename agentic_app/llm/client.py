from __future__ import annotations

from typing import Any, Dict, List, Optional

from agentic_app.config import settings


class LLMClient:
    """Thin wrapper around the OpenAI chat completions API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> None:
        api_key = api_key or settings.openai_api_key
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. Set it in your environment or .env file."
            )

        # Import lazily so test environments that stub the LLM do not require
        # the OpenAI package at import time.
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model or settings.openai_model
        self._temperature = (
            settings.temperature if temperature is None else float(temperature)
        )

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str | Dict[str, Any] | None = "auto",
    ) -> Any:
        """
        Call the chat completions API and return the first message.

        The return type is the raw SDK message object so the agent can
        access .content and .tool_calls directly.
        """
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=self._temperature,
        )
        return response.choices[0].message
