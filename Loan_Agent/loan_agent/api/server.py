from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from loan_agent.agent.runner import run_underwriting_agent
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
    applicant_id: str
    loan_id: Optional[str] = None
    months: int = Field(default=6, ge=1, le=24)
    model: str = "gpt-4.1-mini"


app = FastAPI(title="Loan Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
        return run_underwriting_agent(
            applicant_id=req.applicant_id,
            loan_id=req.loan_id,
            months=req.months,
            model=req.model,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

