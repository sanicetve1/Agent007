from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from loan_agent.agent.policy import merge_underwriting_signals
from loan_agent.agent.schemas import LoanSelectionOption, UnderwritingAgentOutput
from loan_agent.tool_registry import execute_tool
from loan_agent.tools import (  # noqa: F401  Ensures tool registration on import.
    analyze_cashflow,
    assess_collateral,
    calculate_credit_risk,
    list_applicant_loans,
)


def _run_tool_with_retry(name: str, args: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Execute a registered tool with one retry on failure.
    """
    last_error: Optional[Exception] = None
    for _ in range(2):
        try:
            return execute_tool(name, **args), None
        except Exception as exc:  # pragma: no cover - defensive runtime behavior
            last_error = exc
    return None, str(last_error) if last_error else "Unknown tool error"


def _trim_history(history: List[Dict[str, Any]], max_items: int) -> List[Dict[str, Any]]:
    return history[-max_items:]


def _render_explanation_with_sdk(
    applicant_id: str,
    credit: Dict[str, Any],
    cashflow: Dict[str, Any],
    collateral: Dict[str, Any],
    overall_risk_level: str,
    recommendation: str,
    model: str,
) -> str:
    """
    Use OpenAI Responses API to generate a concise human-readable explanation.
    """
    try:
        from openai import OpenAI
    except ImportError:
        return (
            "Underwriting decision generated from deterministic tool signals. "
            "Install the openai package to generate LLM explanations."
        )

    try:
        client = OpenAI()
        prompt = {
            "applicant_id": applicant_id,
            "credit_risk": credit,
            "cashflow_signal": cashflow,
            "collateral_status": collateral,
            "overall_risk_level": overall_risk_level,
            "recommendation": recommendation,
        }
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are an underwriting assistant. Explain the final recommendation in 2-4 sentences, "
                        "referencing only provided tool outputs. Do not invent numbers."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt),
                },
            ],
        )
        return response.output_text.strip()
    except Exception:
        return ""


def run_underwriting_agent(
    applicant_id: str,
    loan_id: Optional[str] = None,
    months: int = 6,
    model: str = "gpt-4.1-mini",
    max_memory_items: int = 10,
) -> Dict[str, Any]:
    """
    Run deterministic tool pipeline plus LLM explanation using OpenAI Responses API.

    Tool order:
    1) calculate_credit_risk
    2) analyze_cashflow
    3) list_applicant_loans -> assess_collateral
    """
    memory_history: List[Dict[str, Any]] = []
    tool_failed = False
    missing_data: List[str] = []

    credit_risk: Dict[str, Any] = {}
    cashflow_signal: Dict[str, Any] = {}
    collateral_status: Dict[str, Any] = {}

    # Step 1: credit risk
    credit_risk, err = _run_tool_with_retry("calculate_credit_risk", {"applicant_id": applicant_id})
    if err:
        tool_failed = True
        missing_data.append("credit_risk")
        credit_risk = {"risk_level": "unknown", "recommendation": "unknown", "error": err}
    memory_history.append({"tool": "calculate_credit_risk", "args": {"applicant_id": applicant_id}, "result": credit_risk})

    # Step 2: cashflow
    cashflow_signal, err = _run_tool_with_retry("analyze_cashflow", {"applicant_id": applicant_id, "months": months})
    if err:
        tool_failed = True
        missing_data.append("cashflow_signal")
        cashflow_signal = {"recommendation": "unknown", "signals": {}, "error": err}
    memory_history.append(
        {
            "tool": "analyze_cashflow",
            "args": {"applicant_id": applicant_id, "months": months},
            "result": cashflow_signal,
        }
    )

    # Step 3: loan selection and collateral
    loan_choices, err = _run_tool_with_retry("list_applicant_loans", {"applicant_id": applicant_id})
    if err or loan_choices is None:
        tool_failed = True
        missing_data.append("loan_choices")
        loan_choices = {"loan_choices": [], "loan_count": 0, "requires_selection": False}
    memory_history.append({"tool": "list_applicant_loans", "args": {"applicant_id": applicant_id}, "result": loan_choices})
    memory_history = _trim_history(memory_history, max_memory_items)

    loan_options = [
        LoanSelectionOption(
            loan_id=item["loan_id"],
            loan_type=item["loan_type"],
            outstanding_amount=float(item["outstanding_amount"]),
            status=item["status"],
            start_date=item["start_date"],
        )
        for item in loan_choices.get("loan_choices", [])
    ]

    if loan_id is None:
        if len(loan_options) == 1:
            loan_id = loan_options[0].loan_id
        elif len(loan_options) > 1:
            result = UnderwritingAgentOutput(
                applicant_id=applicant_id,
                credit_risk=credit_risk,
                cashflow_signal=cashflow_signal,
                collateral_status={},
                overall_risk_level="medium",
                recommendation="conditional",
                explanation="Multiple active loans found. Please select one loan_id to continue collateral assessment.",
                tool_failed=tool_failed,
                missing_data=sorted(set(missing_data)),
                loan_selection_required=True,
                loan_options=loan_options,
                selected_loan_id=None,
            )
            return result.to_dict()

    if loan_id:
        collateral_status, err = _run_tool_with_retry("assess_collateral", {"loan_id": loan_id})
        if err:
            tool_failed = True
            missing_data.append("collateral_status")
            collateral_status = {"collateral_status": "unknown", "recommendation": "unknown", "error": err}
        memory_history.append({"tool": "assess_collateral", "args": {"loan_id": loan_id}, "result": collateral_status})
        memory_history = _trim_history(memory_history, max_memory_items)
    else:
        missing_data.append("collateral_status")
        collateral_status = {"collateral_status": "unknown", "recommendation": "unknown"}

    overall_risk, recommendation, fallback_explanation, missing_from_policy = merge_underwriting_signals(
        credit_risk=credit_risk,
        cashflow_signal=cashflow_signal,
        collateral_status=collateral_status,
        tool_failed=tool_failed,
    )
    missing_data.extend(missing_from_policy)
    missing_data = sorted(set(missing_data))

    explanation = _render_explanation_with_sdk(
        applicant_id=applicant_id,
        credit=credit_risk,
        cashflow=cashflow_signal,
        collateral=collateral_status,
        overall_risk_level=overall_risk,
        recommendation=recommendation,
        model=model,
    )
    if not explanation:
        explanation = fallback_explanation

    result = UnderwritingAgentOutput(
        applicant_id=applicant_id,
        credit_risk=credit_risk,
        cashflow_signal=cashflow_signal,
        collateral_status=collateral_status,
        overall_risk_level=overall_risk,
        recommendation=recommendation,
        explanation=explanation,
        tool_failed=tool_failed,
        missing_data=missing_data,
        loan_selection_required=False,
        loan_options=loan_options,
        selected_loan_id=loan_id,
    )
    return result.to_dict()

