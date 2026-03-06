from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from loan_agent.agent.policy import merge_underwriting_signals
from loan_agent.agent.schemas import LoanSelectionOption, ToolCallTrace, UnderwritingAgentOutput
from loan_agent.tool_registry import execute_tool
from loan_agent.tools import (  # noqa: F401  Ensures tool registration on import.
    analyze_cashflow,
    assess_collateral,
    calculate_credit_risk,
    list_applicant_loans,
)


def _run_tool_with_retry(name: str, args: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    """
    Execute a registered tool with one retry on failure.
    """
    last_error: Optional[Exception] = None
    for _ in range(2):
        try:
            return execute_tool(name, **args), None, _ + 1
        except Exception as exc:  # pragma: no cover - defensive runtime behavior
            last_error = exc
    return None, str(last_error) if last_error else "Unknown tool error", 2


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


def _render_outcome_analysis_with_sdk(
    payload: Dict[str, Any],
    model: str,
) -> Dict[str, Any]:
    """
    Generate a structured LLM Suggestion: customer info used, analysis findings, final verdict.
    Keeps approval_summary/key_strengths/key_risks for backward compatibility.
    """
    fallback = {
        "approval_summary": payload.get("explanation", ""),
        "decision": payload.get("recommendation", "conditional"),
        "overall_risk_level": payload.get("overall_risk_level", "medium"),
        "key_strengths": [],
        "key_risks": payload.get("missing_data", []),
        "next_actions": ["Review tool outputs and missing data before final approval."],
        "customer_information_used": [],
        "analysis_findings": [],
        "final_verdict": payload.get("explanation", ""),
    }
    try:
        from openai import OpenAI
    except ImportError:
        return fallback

    try:
        client = OpenAI()
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior underwriting analyst. Return STRICT JSON only with these keys:\n"
                        "- customer_information_used (string array): Bullet points listing what customer data was used to analyze. "
                        "Include: 1) Customer loan data (outstanding amounts, loan type, status), 2) Customer risk profile (credit score, DTI, risk level from tools), "
                        "3) Income and cashflow (income, expenses, volatility, net cashflow), 4) Any other rules/signals run (e.g. collateral, cashflow stability).\n"
                        "- analysis_findings (string array): Bullet points of what the analysis shows, e.g. 'Vulnerable to low income volatility', 'Strong collateral coverage', "
                        "'High DTI concern'. Base only on the provided tool outputs.\n"
                        "- final_verdict (string): One or two sentences: 'Based on the boundaries defined in our rules, this customer can be provided [approval/conditional/decline].' "
                        "Reference the policy recommendation.\n"
                        "- decision (string), overall_risk_level (string), key_strengths (string array), key_risks (string array), next_actions (string array).\n"
                        "Base everything ONLY on the provided tool outputs; do not invent numbers."
                    ),
                },
                {"role": "user", "content": json.dumps(payload)},
            ],
        )
        text = (response.output_text or "").strip()
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            out = {
                "approval_summary": str(parsed.get("approval_summary", fallback["approval_summary"])),
                "decision": str(parsed.get("decision", fallback["decision"])),
                "overall_risk_level": str(parsed.get("overall_risk_level", fallback["overall_risk_level"])),
                "key_strengths": list(parsed.get("key_strengths", fallback["key_strengths"])),
                "key_risks": list(parsed.get("key_risks", fallback["key_risks"])),
                "next_actions": list(parsed.get("next_actions", fallback["next_actions"])),
                "customer_information_used": list(parsed.get("customer_information_used", fallback["customer_information_used"])),
                "analysis_findings": list(parsed.get("analysis_findings", fallback["analysis_findings"])),
                "final_verdict": str(parsed.get("final_verdict", fallback["final_verdict"])),
            }
            return out
    except Exception:
        return fallback
    return fallback


def _render_chat_answer_with_sdk(
    question: str,
    payload: Dict[str, Any],
    model: str,
) -> str:
    """
    Generate a natural-language answer for customer chat, grounded in tool
    outputs / underwriting signals.
    """
    try:
        from openai import OpenAI
    except ImportError:
        # Fallback: very simple textual answer using existing explanation.
        base = payload.get("explanation") or ""
        if not base:
            base = "I do not have enough structured data to answer in detail."
        return (
            f"Here is what I can say based on the available underwriting data:\n\n"
            f"{base}\n\n"
            f"(Install the openai package to enable richer, question-specific chat answers.)"
        )

    try:
        client = OpenAI()
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a customer insights assistant for retail lending. "
                        "Answer the user's question ONLY using the structured data provided. "
                        "If the question cannot be answered exactly, say so and provide the closest facts. "
                        "Do not invent numbers or products; do not guess."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": question,
                            "underwriting_context": payload,
                        }
                    ),
                },
            ],
        )
        text = (response.output_text or "").strip()
        return text or ""
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
    tool_call_sequence: List[ToolCallTrace] = []

    credit_risk: Dict[str, Any] = {}
    cashflow_signal: Dict[str, Any] = {}
    collateral_status: Dict[str, Any] = {}

    # Step 1: credit risk
    credit_args = {"applicant_id": applicant_id}
    credit_risk, err, attempts = _run_tool_with_retry("calculate_credit_risk", credit_args)
    if err:
        tool_failed = True
        missing_data.append("credit_risk")
        credit_risk = {"risk_level": "unknown", "recommendation": "unknown", "error": err}
    memory_history.append({"tool": "calculate_credit_risk", "args": credit_args, "result": credit_risk})
    tool_call_sequence.append(
        ToolCallTrace(
            step=1,
            tool="calculate_credit_risk",
            args=credit_args,
            status="failed" if err else "success",
            attempts=attempts,
            error=err,
            result=credit_risk,
        )
    )

    # Step 2: cashflow
    cashflow_args = {"applicant_id": applicant_id, "months": months}
    cashflow_signal, err, attempts = _run_tool_with_retry("analyze_cashflow", cashflow_args)
    if err:
        tool_failed = True
        missing_data.append("cashflow_signal")
        cashflow_signal = {"recommendation": "unknown", "signals": {}, "error": err}
    memory_history.append(
        {
            "tool": "analyze_cashflow",
            "args": cashflow_args,
            "result": cashflow_signal,
        }
    )
    tool_call_sequence.append(
        ToolCallTrace(
            step=2,
            tool="analyze_cashflow",
            args=cashflow_args,
            status="failed" if err else "success",
            attempts=attempts,
            error=err,
            result=cashflow_signal,
        )
    )

    # Step 3: loan selection and collateral
    loan_list_args = {"applicant_id": applicant_id}
    loan_choices, err, attempts = _run_tool_with_retry("list_applicant_loans", loan_list_args)
    if err or loan_choices is None:
        tool_failed = True
        missing_data.append("loan_choices")
        loan_choices = {"loan_choices": [], "loan_count": 0, "requires_selection": False}
    memory_history.append({"tool": "list_applicant_loans", "args": loan_list_args, "result": loan_choices})
    memory_history = _trim_history(memory_history, max_memory_items)
    tool_call_sequence.append(
        ToolCallTrace(
            step=3,
            tool="list_applicant_loans",
            args=loan_list_args,
            status="failed" if err else "success",
            attempts=attempts,
            error=err,
            result=loan_choices,
        )
    )

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
                tool_call_sequence=tool_call_sequence,
                llm_outcome_analysis={
                    "approval_summary": "Loan selection is required before collateral assessment can proceed.",
                    "decision": "conditional",
                    "overall_risk_level": "medium",
                    "key_strengths": [],
                    "key_risks": ["multiple_active_loans"],
                    "next_actions": ["Select a loan_id and rerun full underwriting."],
                },
            )
            return result.to_dict()

    if loan_id:
        collateral_args = {"loan_id": loan_id}
        collateral_status, err, attempts = _run_tool_with_retry("assess_collateral", collateral_args)
        if err:
            tool_failed = True
            missing_data.append("collateral_status")
            collateral_status = {"collateral_status": "unknown", "recommendation": "unknown", "error": err}
        memory_history.append({"tool": "assess_collateral", "args": collateral_args, "result": collateral_status})
        memory_history = _trim_history(memory_history, max_memory_items)
        tool_call_sequence.append(
            ToolCallTrace(
                step=4,
                tool="assess_collateral",
                args=collateral_args,
                status="failed" if err else "success",
                attempts=attempts,
                error=err,
                result=collateral_status,
            )
        )
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

    llm_outcome_analysis = _render_outcome_analysis_with_sdk(
        payload={
            "applicant_id": applicant_id,
            "credit_risk": credit_risk,
            "cashflow_signal": cashflow_signal,
            "collateral_status": collateral_status,
            "overall_risk_level": overall_risk,
            "recommendation": recommendation,
            "tool_failed": tool_failed,
            "missing_data": missing_data,
            "tool_call_sequence": [t.__dict__ for t in tool_call_sequence],
            "explanation": explanation,
        },
        model=model,
    )

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
        tool_call_sequence=tool_call_sequence,
        llm_outcome_analysis=llm_outcome_analysis,
    )
    return result.to_dict()

