from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg

from loan_agent.config import settings


def _dsn() -> str:
    return (
        f"host={settings.host} "
        f"port={settings.port} "
        f"dbname={settings.name} "
        f"user={settings.user} "
        f"password={settings.password}"
    )


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(_dsn())
    try:
        yield conn
    finally:
        conn.close()

