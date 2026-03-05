from loan_agent.tools.assess_collateral import COLLATERAL_TOOL_SPEC, assess_collateral
from loan_agent.tools.analyze_cashflow_stability import (
    ANALYZE_CASHFLOW_TOOL_SPEC,
    CASHFLOW_STABILITY_TOOL_SPEC,
    analyze_cashflow,
    analyze_cashflow_stability,
)
from loan_agent.tools.calculate_credit_risk import (
    CREDIT_RISK_TOOL_SPEC,
    calculate_credit_risk,
)
from loan_agent.tools.list_applicant_loans import (
    LIST_APPLICANT_LOANS_TOOL_SPEC,
    list_applicant_loans,
)
from loan_agent.tool_registry import register_tool

register_tool(COLLATERAL_TOOL_SPEC)
register_tool(ANALYZE_CASHFLOW_TOOL_SPEC)
register_tool(CREDIT_RISK_TOOL_SPEC)
register_tool(LIST_APPLICANT_LOANS_TOOL_SPEC)

__all__ = [
    "assess_collateral",
    "analyze_cashflow",
    "analyze_cashflow_stability",
    "calculate_credit_risk",
    "list_applicant_loans",
]

