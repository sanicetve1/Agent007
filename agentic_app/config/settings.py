from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    """Central configuration for the agentic app."""

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.0"))
    enable_memory: bool = os.getenv("ENABLE_MEMORY", "false").lower() == "true"

    def validate(self) -> None:
        if not self.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Please configure it in your .env file."
            )


settings = Settings()

