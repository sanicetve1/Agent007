"""
Resolve applicants by name for chat/clarification (MVP: unique or disambiguate by listing).
"""
from __future__ import annotations

from typing import Any, Dict, List

from loan_agent.db import get_conn


def resolve_applicants_by_name(name: str) -> List[Dict[str, Any]]:
    """
    Search applicants by full_name (case-insensitive, partial match).
    Returns list of {"applicant_id": str, "full_name": str}; empty if none.
    """
    if not (name or "").strip():
        return []
    search = f"%{(name or '').strip()}%"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT applicant_id, full_name
            FROM applicants
            WHERE full_name ILIKE %s
            ORDER BY full_name
            LIMIT 20
            """,
            (search,),
        )
        rows = cur.fetchall()
    return [{"applicant_id": str(r[0]), "full_name": r[1]} for r in rows]
