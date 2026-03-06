from __future__ import annotations

import os
from pathlib import Path

from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env: CWD first, then package root (Loan_Agent) with override so Loan_Agent/.env wins
_loan_agent_root = Path(__file__).resolve().parent.parent
_cwd_env = Path.cwd() / ".env"
_env_file = _loan_agent_root / ".env"
if _cwd_env.exists():
    load_dotenv(_cwd_env)
if _env_file.exists():
    load_dotenv(_env_file, override=True)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off", ""):
        return False
    return default


@dataclass(frozen=True)
class DBSettings:
    host: str = os.getenv("LOAN_DB_HOST", "localhost")
    port: int = int(os.getenv("LOAN_DB_PORT", "5432"))
    name: str = os.getenv("LOAN_DB_NAME", "loan_db")
    user: str = os.getenv("LOAN_DB_USER", "admin")
    password: str = os.getenv("LOAN_DB_PASSWORD", "admin")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class AgentSettings:
    """When True, use the autonomous ReAct agent; when False, use the deterministic pipeline."""
    enable_autonomy: bool = _env_bool("ENABLE_AUTONOMY", False)
    """Max tool-execution steps in autonomous mode before forcing decision or informing user."""
    max_steps: int = _env_int("AGENT_MAX_STEPS", 8)


settings = DBSettings()
agent_settings = AgentSettings()

