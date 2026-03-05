from __future__ import annotations

from typing import Any, Dict, List, Tuple


_RISK_SCORE = {"low": 1, "medium": 2, "high": 3, "adequate": 1, "borderline": 2, "insufficient": 3}


def _max_risk(*values: str) -> str:
    filtered = [v for v in values if v in {"low", "medium", "high"}]
    if not filtered:
        return "medium"
    return max(filtered, key=lambda x: _RISK_SCORE[x])


def merge_underwriting_signals(
    credit_risk: Dict[str, Any],
    cashflow_signal: Dict[str, Any],
    collateral_status: Dict[str, Any],
    tool_failed: bool = False,
) -> Tuple[str, str, str, List[str]]:
    """
    Deterministic merge policy for overall risk and recommendation.
    """
    missing_data: List[str] = []

    credit_level = str(credit_risk.get("risk_level", "unknown")).lower()
    if credit_level not in {"low", "medium", "high"}:
        missing_data.append("credit_risk")
        credit_level = "medium"

    cashflow_reco = str(cashflow_signal.get("recommendation", "")).lower()
    if not cashflow_signal:
        missing_data.append("cashflow_signal")
    cashflow_level = "medium"
    if "high cashflow risk" in cashflow_reco:
        cashflow_level = "high"
    elif "stable cashflow" in cashflow_reco and "minor" not in cashflow_reco:
        cashflow_level = "low"

    collateral_band = str(collateral_status.get("collateral_status", "unknown")).lower()
    if collateral_band not in {"adequate", "borderline", "insufficient"}:
        missing_data.append("collateral_status")
        collateral_level = "medium"
    else:
        collateral_level = {1: "low", 2: "medium", 3: "high"}[_RISK_SCORE[collateral_band]]

    overall = _max_risk(credit_level, cashflow_level, collateral_level)

    if tool_failed:
        recommendation = "conditional"
    elif overall == "high":
        recommendation = "decline"
    elif overall == "medium":
        recommendation = "conditional"
    else:
        recommendation = "approve"

    explanation = (
        f"Combined assessment from credit ({credit_level}), cashflow ({cashflow_level}), "
        f"and collateral ({collateral_band if collateral_band != 'unknown' else 'unavailable'}) results in "
        f"overall {overall} risk with {recommendation} recommendation."
    )
    return overall, recommendation, explanation, missing_data

