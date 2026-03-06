from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from loan_agent.agent import run_autonomous_continue, run_autonomous_underwriting_agent, run_customer_chat, run_underwriting_agent
from loan_agent.config import agent_settings
from loan_agent.db import get_conn
from loan_agent.tools import (
    analyze_cashflow,
    assess_collateral,
    calculate_credit_risk,
    list_applicant_loans,
)


class ApplicantSummary(BaseModel):
    applicant_id: str
    full_name: str
    annual_income: float
    kyc_status: str


class CreditRiskReq(BaseModel):
    applicant_id: str


class CashflowReq(BaseModel):
    applicant_id: str
    months: int = Field(default=6, ge=1, le=24)


class ListLoansReq(BaseModel):
    applicant_id: str
    include_closed: bool = False


class AssessCollateralReq(BaseModel):
    loan_id: str
    threshold_ratio: float = Field(default=1.0, gt=0)


class UnderwritingReq(BaseModel):
    applicant_id: Optional[str] = None
    loan_id: Optional[str] = None
    months: int = Field(default=6, ge=1, le=24)
    model: str = "gpt-4.1-mini"


class AgentContinueReq(BaseModel):
    session_id: str
    user_reply: str
    model: str = "gpt-4.1-mini"


class AgentChatReq(BaseModel):
    applicant_id: str
    message: str
    session_id: Optional[str] = None
    model: str = "gpt-4.1-mini"


app = FastAPI(title="Loan Agent API", version="0.1.0")
logger = logging.getLogger(__name__)


@app.on_event("startup")
def _log_agent_mode() -> None:
    mode = "autonomous" if agent_settings.enable_autonomy else "deterministic"
    print(f"Loan Agent API: mode={mode} (ENABLE_AUTONOMY={agent_settings.enable_autonomy})")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/data/applicants", response_model=List[ApplicantSummary])
async def list_applicants(limit: int = 20) -> List[ApplicantSummary]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT applicant_id, full_name, annual_income, kyc_status
            FROM applicants
            ORDER BY created_at ASC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
    return [
        ApplicantSummary(
            applicant_id=str(r[0]),
            full_name=r[1],
            annual_income=float(r[2]),
            kyc_status=r[3],
        )
        for r in rows
    ]


@app.post("/tools/calculate_credit_risk")
async def tool_calculate_credit_risk(req: CreditRiskReq) -> Dict[str, Any]:
    try:
        return calculate_credit_risk(req.applicant_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/tools/analyze_cashflow")
async def tool_analyze_cashflow(req: CashflowReq) -> Dict[str, Any]:
    try:
        return analyze_cashflow(req.applicant_id, req.months)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/tools/list_applicant_loans")
async def tool_list_applicant_loans(req: ListLoansReq) -> Dict[str, Any]:
    try:
        return list_applicant_loans(req.applicant_id, req.include_closed)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/tools/assess_collateral")
async def tool_assess_collateral(req: AssessCollateralReq) -> Dict[str, Any]:
    try:
        return assess_collateral(req.loan_id, req.threshold_ratio)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/agent/run")
async def run_agent(req: UnderwritingReq) -> Dict[str, Any]:
    try:
        applicant_id = req.applicant_id or ""
        if agent_settings.enable_autonomy:
            return run_autonomous_underwriting_agent(
                applicant_id=applicant_id,
                loan_id=req.loan_id,
                months=req.months,
                model=req.model,
            )
        if not applicant_id:
            raise HTTPException(status_code=400, detail="applicant_id required for deterministic mode")
        result = run_underwriting_agent(
            applicant_id=applicant_id,
            loan_id=req.loan_id,
            months=req.months,
            model=req.model,
        )
        result["agent_mode"] = "deterministic"
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/agent/continue")
async def agent_continue(req: AgentContinueReq) -> Dict[str, Any]:
    """Continue after clarification: send session_id and user_reply (e.g. applicant_id UUID or text)."""
    try:
        if not agent_settings.enable_autonomy:
            raise HTTPException(status_code=400, detail="ENABLE_AUTONOMY must be true to use /agent/continue")
        return run_autonomous_continue(
            session_id=req.session_id,
            user_reply=req.user_reply,
            model=req.model,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/agent/chat")
async def agent_chat(req: AgentChatReq) -> Dict[str, Any]:
    """
    Customer-context chat endpoint.

    Uses the autonomous ReAct agent in `customer_chat` mode so the agent can
    answer focused questions about a specific applicant, using tools when
    needed. One logical chat session per applicant (per client) is tracked via
    session_id.
    """
    try:
        if not agent_settings.enable_autonomy:
            raise HTTPException(status_code=400, detail="ENABLE_AUTONOMY must be true to use /agent/chat")
        return run_customer_chat(
            applicant_id=req.applicant_id,
            message=req.message,
            session_id=req.session_id,
            model=req.model,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

