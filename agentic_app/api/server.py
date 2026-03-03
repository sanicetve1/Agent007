from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agentic_app.agent import Agent
from agentic_app.agent.state import TraceStep


class RunRequest(BaseModel):
    input: str


class RunResponse(BaseModel):
    trace: List[Dict[str, Any]]
    final_response: str


app = FastAPI(title="Agent007 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/agent/run", response_model=RunResponse)
async def run_agent(req: RunRequest) -> RunResponse:
    """
    Run the agent once and return its execution trace and final response.

    This endpoint is stateless from the server's perspective; the React UI
    can use it to visualize single-run workflows.
    """
    agent = Agent()
    state = agent.run(req.input)

    def to_dict(step: TraceStep) -> Dict[str, Any]:
        return {"step": step.step, "info": step.info}

    trace = [to_dict(s) for s in state.trace_steps]
    return RunResponse(trace=trace, final_response=state.final_response or "")

