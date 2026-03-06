"""
AgentContext: single source of truth for the autonomous ReAct agent.

All nodes read from and write to AgentContext. No direct node-to-node calls;
the state machine / Router determines the next edge from context.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class IntentOutput:
    intent_type: str  # full_underwriting | credit_only | general_question
    entities: Dict[str, Any]  # applicant_id?, loan_id?, months?
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


@dataclass
class PlanningOutput:
    tool_horizon: List[str]  # eligible tool names (no order)
    notes: Optional[str] = None


@dataclass
class TraceStep:
    step_type: str  # intent | plan | tool | observation | reasoning | decision
    step_index: int
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolHistoryEntry:
    tool: str
    args: Dict[str, Any]
    result: Dict[str, Any]
    status: str  # success | failed
    attempts: int = 1
    error: Optional[str] = None


@dataclass
class AgentContext:
    """
    Shared context for the ReAct agent. All nodes read/write this.
    """

    # --- User input layer ---
    user_request: str = ""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # --- Extracted / derived ---
    intent: Optional[IntentOutput] = None
    planning: Optional[PlanningOutput] = None
    tool_history: List[ToolHistoryEntry] = field(default_factory=list)
    signals: Dict[str, Any] = field(default_factory=lambda: {
        "credit_risk": {},
        "cashflow_signal": {},
        "collateral_status": {},
    })
    policy_decision: Dict[str, Any] = field(default_factory=dict)  # overall_risk_level, recommendation, explanation
    llm_explanation: str = ""
    llm_outcome_analysis: Dict[str, Any] = field(default_factory=dict)

    # --- Trace and control ---
    trace: List[TraceStep] = field(default_factory=list)
    agent_state: str = "intent"  # intent | planning | routing | tool | observing | reasoning | decision | done | clarification

    # --- Clarification (after Intent only) ---
    clarification_required: bool = False
    clarification_question: Optional[str] = None

    # --- Reasoning outputs (goal_met, confidence) ---
    goal_met: bool = False
    confidence: float = 0.0

    # --- Loop control (set by state machine) ---
    max_steps_reached: bool = False

    def append_trace(self, step_type: str, detail: Optional[Dict[str, Any]] = None) -> None:
        self.trace.append(
            TraceStep(step_type=step_type, step_index=len(self.trace) + 1, detail=detail or {})
        )

    def append_tool_entry(self, tool: str, args: Dict[str, Any], result: Dict[str, Any], status: str, attempts: int = 1, error: Optional[str] = None) -> None:
        self.tool_history.append(
            ToolHistoryEntry(tool=tool, args=args, result=result, status=status, attempts=attempts, error=error)
        )

    @property
    def entities(self) -> Dict[str, Any]:
        if self.intent is None:
            return {}
        return self.intent.entities.copy()

    @property
    def applicant_id(self) -> Optional[str]:
        return (self.intent and self.intent.entities.get("applicant_id")) or None

    @property
    def loan_id(self) -> Optional[str]:
        return (self.intent and self.intent.entities.get("loan_id")) or self.signals.get("_loan_id")

    @property
    def months(self) -> int:
        return int((self.intent and self.intent.entities.get("months")) or 6)
