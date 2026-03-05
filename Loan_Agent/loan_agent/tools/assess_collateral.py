from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict
from uuid import UUID

from loan_agent.db import get_conn
from loan_agent.tool_registry import ToolSpec


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _coverage_band(ratio: float, threshold_ratio: float) -> str:
    if ratio >= threshold_ratio:
        return "adequate"
    if ratio >= 0.8:
        return "borderline"
    return "insufficient"


def assess_collateral(loan_id: str, threshold_ratio: float = 1.0) -> Dict[str, Any]:
    """
    Evaluate collateral adequacy for a specific loan.
    """
    try:
        UUID(loan_id)
    except ValueError as exc:
        raise ValueError("loan_id must be a valid UUID string") from exc

    if threshold_ratio <= 0:
        raise ValueError("threshold_ratio must be greater than 0")

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT loan_id, loan_type, principal_amount, outstanding_amount
            FROM loans
            WHERE loan_id = %s
            """,
            (loan_id,),
        )
        loan = cur.fetchone()
        if not loan:
            raise ValueError(f"Loan not found: {loan_id}")

        cur.execute(
            """
            SELECT asset_type, asset_value, valuation_date
            FROM collateral
            WHERE loan_id = %s
            ORDER BY valuation_date DESC
            """,
            (loan_id,),
        )
        rows = cur.fetchall()

    outstanding_amount = _to_decimal(loan[3])
    if outstanding_amount <= 0:
        raise ValueError(f"Invalid outstanding_amount for loan: {loan_id}")

    total_collateral_value = sum((_to_decimal(r[1]) for r in rows), Decimal("0"))
    coverage_ratio = float(total_collateral_value / outstanding_amount)

    stale_cutoff = date.today() - timedelta(days=365)
    has_outdated_collateral = any(r[2] < stale_cutoff for r in rows)

    risk_level = _coverage_band(coverage_ratio, threshold_ratio)
    if not rows:
        recommendation = "no collateral found"
    elif risk_level == "adequate" and not has_outdated_collateral:
        recommendation = "collateral is adequate"
    elif risk_level == "adequate" and has_outdated_collateral:
        recommendation = "collateral adequate but revaluation recommended"
    elif risk_level == "borderline":
        recommendation = "borderline collateral coverage"
    else:
        recommendation = "insufficient collateral coverage"

    return {
        "loan_id": str(loan[0]),
        "loan_type": loan[1],
        "principal_amount": float(_to_decimal(loan[2])),
        "outstanding_amount": float(outstanding_amount),
        "collateral_count": len(rows),
        "total_collateral_value": float(total_collateral_value),
        "coverage_ratio": round(coverage_ratio, 4),
        "threshold_ratio": threshold_ratio,
        "collateral_status": risk_level,
        "signals": {
            "outdated_collateral": has_outdated_collateral,
            "missing_collateral": len(rows) == 0,
        },
        "recommendation": recommendation,
        "metadata": {
            "confidence": "high" if rows else "low",
            "warnings": ["no_collateral_records"] if not rows else [],
        },
    }


COLLATERAL_TOOL_SPEC = ToolSpec(
    name="assess_collateral",
    description="Assess collateral adequacy and coverage ratio for a loan.",
    input_schema={
        "type": "object",
        "properties": {
            "loan_id": {
                "type": "string",
                "description": "Loan UUID.",
                "format": "uuid",
            },
            "threshold_ratio": {
                "type": "number",
                "description": "Minimum coverage ratio for adequate collateral (default 1.0).",
                "default": 1.0,
                "exclusiveMinimum": 0,
            },
        },
        "required": ["loan_id"],
        "additionalProperties": False,
    },
    fn=assess_collateral,
)

