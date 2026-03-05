from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class DBSettings:
    host: str = os.getenv("LOAN_DB_HOST", "localhost")
    port: int = int(os.getenv("LOAN_DB_PORT", "5432"))
    name: str = os.getenv("LOAN_DB_NAME", "loan_db")
    user: str = os.getenv("LOAN_DB_USER", "admin")
    password: str = os.getenv("LOAN_DB_PASSWORD", "change_me")


settings = DBSettings()

