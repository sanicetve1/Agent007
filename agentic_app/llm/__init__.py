"""LLM layer: provides the chat model used by the graph."""

from __future__ import annotations

from langchain_core.runnables import Runnable

from agentic_app.config import settings


def get_llm() -> Runnable:
    """Return the default LLM (ChatOpenAI from config) for the agent graph."""
    from langchain_openai import ChatOpenAI
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. Set it in your .env file."
        )
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=settings.temperature,
    )


__all__ = ["get_llm"]
