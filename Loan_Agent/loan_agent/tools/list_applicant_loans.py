from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from loan_agent.db import get_conn
from loan_agent.tool_registry import ToolSpec


def list_applicant_loans(applicant_id: str, include_closed: bool = False) -> Dict[str, Any]:
    """
    List loan choices for an applicant before collateral assessment.
    """
    try:
        UUID(applicant_id)
    except ValueError as exc:
        raise ValueError("applicant_id must be a valid UUID string") from exc

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT applicant_id
            FROM applicants
            WHERE applicant_id = %s
            """,
            (applicant_id,),
        )
        if not cur.fetchone():
            raise ValueError(f"Applicant not found: {applicant_id}")

        if include_closed:
            cur.execute(
                """
                SELECT loan_id, loan_type, outstanding_amount, status, start_date
                FROM loans
                WHERE applicant_id = %s
                ORDER BY outstanding_amount DESC, start_date DESC
                """,
                (applicant_id,),
            )
        else:
            cur.execute(
                """
                SELECT loan_id, loan_type, outstanding_amount, status, start_date
                FROM loans
                WHERE applicant_id = %s
                  AND status = 'active'
                ORDER BY outstanding_amount DESC, start_date DESC
                """,
                (applicant_id,),
            )
        rows = cur.fetchall()

    choices: List[Dict[str, Any]] = [
        {
            "loan_id": str(r[0]),
            "loan_type": r[1],
            "outstanding_amount": float(r[2]),
            "status": r[3],
            "start_date": r[4].isoformat(),
        }
        for r in rows
    ]

    return {
        "applicant_id": applicant_id,
        "loan_choices": choices,
        "loan_count": len(choices),
        "requires_selection": len(choices) > 1,
        "recommended_loan_id": choices[0]["loan_id"] if choices else None,
        "metadata": {
            "confidence": "high",
            "warnings": ["no_loans_found"] if not choices else [],
        },
    }


LIST_APPLICANT_LOANS_TOOL_SPEC = ToolSpec(
    name="list_applicant_loans",
    description="List available loans for an applicant to select one for collateral assessment.",
    input_schema={
        "type": "object",
        "properties": {
            "applicant_id": {
                "type": "string",
                "description": "Applicant UUID.",
                "format": "uuid",
            },
            "include_closed": {
                "type": "boolean",
                "description": "Include closed loans in the result.",
                "default": False,
            },
        },
        "required": ["applicant_id"],
        "additionalProperties": False,
    },
    fn=list_applicant_loans,
)

