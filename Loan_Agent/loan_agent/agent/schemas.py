from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LoanSelectionOption:
    loan_id: str
    loan_type: str
    outstanding_amount: float
    status: str
    start_date: str


@dataclass
class ToolCallTrace:
    step: int
    tool: str
    args: Dict[str, Any]
    status: str
    attempts: int
    error: Optional[str] = None
    result: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnderwritingAgentOutput:
    applicant_id: str
    credit_risk: Dict[str, Any]
    cashflow_signal: Dict[str, Any]
    collateral_status: Dict[str, Any]
    overall_risk_level: str
    recommendation: str
    explanation: str
    tool_failed: bool
    missing_data: List[str] = field(default_factory=list)
    loan_selection_required: bool = False
    loan_options: List[LoanSelectionOption] = field(default_factory=list)
    selected_loan_id: Optional[str] = None
    tool_call_sequence: List[ToolCallTrace] = field(default_factory=list)
    llm_outcome_analysis: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["loan_options"] = [asdict(x) for x in self.loan_options]
        payload["tool_call_sequence"] = [asdict(x) for x in self.tool_call_sequence]
        return payload

