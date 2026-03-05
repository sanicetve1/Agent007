from __future__ import annotations

from datetime import date
from decimal import Decimal
from statistics import pstdev
from typing import Any, Dict
from uuid import UUID

from loan_agent.db import get_conn
from loan_agent.tool_registry import ToolSpec


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _shift_month(d: date, delta: int) -> date:
    y, m = d.year, d.month + delta
    while m <= 0:
        y -= 1
        m += 12
    while m > 12:
        y += 1
        m -= 12
    return date(y, m, 1)


def _build_month_buckets(months: int) -> list[date]:
    current = _month_start(date.today())
    start = _shift_month(current, -(months - 1))
    return [_shift_month(start, i) for i in range(months)]


def _as_float(v: Decimal) -> float:
    return float(v.quantize(Decimal("0.0001")))


def analyze_cashflow(applicant_id: str, months: int = 6) -> Dict[str, Any]:
    """
    Analyze applicant cashflow stability over the recent N months.
    """
    try:
        UUID(applicant_id)
    except ValueError as exc:
        raise ValueError("applicant_id must be a valid UUID string") from exc

    if months < 1 or months > 24:
        raise ValueError("months must be between 1 and 24")

    month_buckets = _build_month_buckets(months)
    start_date = month_buckets[0]

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

        cur.execute(
            """
            SELECT
                DATE_TRUNC('month', txn_date)::date AS month_start,
                COALESCE(SUM(CASE WHEN txn_type = 'credit' THEN amount ELSE 0 END), 0) AS credits,
                COALESCE(SUM(CASE WHEN txn_type = 'debit' THEN amount ELSE 0 END), 0) AS debits,
                COALESCE(SUM(CASE WHEN txn_type = 'debit' AND category = 'emi' THEN amount ELSE 0 END), 0) AS emi_debits
            FROM transactions
            WHERE applicant_id = %s
              AND txn_date >= %s
            GROUP BY 1
            ORDER BY 1
            """,
            (applicant_id, start_date),
        )
        rows = cur.fetchall()

    monthly = {m: {"credits": Decimal("0"), "debits": Decimal("0"), "emi": Decimal("0")} for m in month_buckets}
    for row in rows:
        month_start = row[0]
        if month_start in monthly:
            monthly[month_start]["credits"] = _to_decimal(row[1])
            monthly[month_start]["debits"] = _to_decimal(row[2])
            monthly[month_start]["emi"] = _to_decimal(row[3])

    credit_series = [monthly[m]["credits"] for m in month_buckets]
    debit_series = [monthly[m]["debits"] for m in month_buckets]
    net_series = [credit_series[i] - debit_series[i] for i in range(months)]
    emi_series = [monthly[m]["emi"] for m in month_buckets]

    avg_income = sum(credit_series) / Decimal(months)
    avg_expenses = sum(debit_series) / Decimal(months)
    avg_net = sum(net_series) / Decimal(months)

    income_std = Decimal(str(pstdev([float(v) for v in credit_series]))) if months > 1 else Decimal("0")
    debit_std = Decimal(str(pstdev([float(v) for v in debit_series]))) if months > 1 else Decimal("0")

    income_volatility_ratio = float(income_std / avg_income) if avg_income > 0 else 1.0
    debit_volatility_ratio = float(debit_std / avg_expenses) if avg_expenses > 0 else 0.0

    emi_months = sum(1 for x in emi_series if x > 0)
    emi_std = Decimal(str(pstdev([float(v) for v in emi_series]))) if months > 1 else Decimal("0")
    emi_avg = sum(emi_series) / Decimal(months)
    emi_irregular = bool(emi_months > 0 and ((emi_months < max(2, months // 2)) or (emi_avg > 0 and float(emi_std / emi_avg) > 0.6)))

    volatile_income = income_volatility_ratio > 0.4
    unstable_expenses = debit_volatility_ratio > 0.5
    cashflow_deficit = avg_net < 0
    payment_risk = emi_irregular

    signal_count = sum([volatile_income, unstable_expenses, cashflow_deficit, payment_risk])
    if cashflow_deficit or signal_count >= 3:
        recommendation = "high cashflow risk"
    elif signal_count >= 1:
        recommendation = "stable cashflow, minor payment risk" if payment_risk else "moderate cashflow risk"
    else:
        recommendation = "stable cashflow"

    return {
        "applicant_id": applicant_id,
        "months_analyzed": months,
        "average_income": _as_float(avg_income),
        "income_std_dev": _as_float(income_std),
        "average_expenses": _as_float(avg_expenses),
        "debit_std_dev": _as_float(debit_std),
        "net_cashflow": _as_float(avg_net),
        "signals": {
            "volatile_income": volatile_income,
            "unstable_expenses": unstable_expenses,
            "cashflow_deficit": cashflow_deficit,
            "payment_risk": payment_risk,
        },
        "recommendation": recommendation,
        "metadata": {
            "confidence": "medium",
            "warnings": [],
        },
    }


ANALYZE_CASHFLOW_TOOL_SPEC = ToolSpec(
    name="analyze_cashflow",
    description="Analyze cashflow stability and risk signals for an applicant.",
    input_schema={
        "type": "object",
        "properties": {
            "applicant_id": {
                "type": "string",
                "description": "Applicant UUID.",
                "format": "uuid",
            },
            "months": {
                "type": "integer",
                "description": "Recent months to analyze (default: 6).",
                "minimum": 1,
                "maximum": 24,
                "default": 6,
            },
        },
        "required": ["applicant_id"],
        "additionalProperties": False,
    },
    fn=analyze_cashflow,
)

# Backward compatibility aliases for early scaffold names.
analyze_cashflow_stability = analyze_cashflow
CASHFLOW_STABILITY_TOOL_SPEC = ANALYZE_CASHFLOW_TOOL_SPEC

