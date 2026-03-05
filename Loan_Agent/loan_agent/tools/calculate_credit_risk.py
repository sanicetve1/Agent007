from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict
from uuid import UUID

from loan_agent.db import get_conn
from loan_agent.tool_registry import ToolSpec


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _classify_risk(credit_score: int, dti: float) -> tuple[str, str]:
    if dti > 0.5 or credit_score < 600:
        return "high", "reject"
    if 0.3 <= dti <= 0.5 and 600 <= credit_score <= 700:
        return "medium", "approve with conditions"
    if dti < 0.3 and credit_score > 700:
        return "low", "approve"
    return "medium", "approve with conditions"


def calculate_credit_risk(applicant_id: str) -> Dict[str, Any]:
    """
    Deterministic underwriting tool.

    DTI formula used in MVP:
    dti = total_active_outstanding / annual_income
    """
    try:
        UUID(applicant_id)
    except ValueError as exc:
        raise ValueError("applicant_id must be a valid UUID string") from exc

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT applicant_id, annual_income, employment_type, kyc_status
            FROM applicants
            WHERE applicant_id = %s
            """,
            (applicant_id,),
        )
        applicant = cur.fetchone()
        if not applicant:
            raise ValueError(f"Applicant not found: {applicant_id}")

        cur.execute(
            """
            SELECT bureau_score
            FROM credit_scores
            WHERE applicant_id = %s
            """,
            (applicant_id,),
        )
        credit_row = cur.fetchone()
        if not credit_row:
            raise ValueError(f"Credit score not found for applicant: {applicant_id}")

        cur.execute(
            """
            SELECT COALESCE(SUM(outstanding_amount), 0)
            FROM loans
            WHERE applicant_id = %s
              AND status = 'active'
            """,
            (applicant_id,),
        )
        loans_row = cur.fetchone()

    annual_income = _to_decimal(applicant[1])
    credit_score = int(credit_row[0])
    total_outstanding = _to_decimal(loans_row[0] if loans_row else 0)

    if annual_income <= 0:
        raise ValueError(f"Invalid annual income for applicant: {applicant_id}")

    dti = float(total_outstanding / annual_income)
    risk_level, recommendation = _classify_risk(credit_score, dti)

    return {
        "applicant_id": str(applicant[0]),
        "credit_score": credit_score,
        "dti": round(dti, 4),
        "risk_level": risk_level,
        "recommendation": recommendation,
        "metadata": {
            "confidence": "high",
            "warnings": [],
        },
    }


CREDIT_RISK_TOOL_SPEC = ToolSpec(
    name="calculate_credit_risk",
    description="Calculate credit risk level for an applicant using DTI and bureau score.",
    input_schema={
        "type": "object",
        "properties": {
            "applicant_id": {
                "type": "string",
                "description": "Applicant UUID.",
                "format": "uuid",
            }
        },
        "required": ["applicant_id"],
        "additionalProperties": False,
    },
    fn=calculate_credit_risk,
)

