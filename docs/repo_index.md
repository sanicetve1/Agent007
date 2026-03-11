# Repository Index

## Project Root

`Agent007/` — Git repository root.

- **Loan_Agent/** — Main application (underwriting agent MVP)
- **Project-plan/** — Planning documents (Agent design, tool categories, data layer, etc.)
- **docs/** — Generated documentation (this folder)
- **planning/** — Roadmap, phases, feature backlog
- **testing/** — Test cases, evaluation notes
- **ops/** — Observability, security

## Loan_Agent Layout

```
Loan_Agent/
├── loan_agent/                    # Python package
│   ├── agent/                     # Agent logic
│   │   ├── context.py            # AgentContext, IntentOutput, PlanningOutput
│   │   ├── policy.py             # merge_underwriting_signals
│   │   ├── runner.py             # Deterministic pipeline
│   │   ├── runner_autonomous.py  # ReAct + clarification + chat
│   │   ├── schemas.py            # UnderwritingAgentOutput, ToolCallTrace
│   │   ├── state_machine.py      # run_react_loop
│   │   └── nodes/
│   │       ├── intent.py
│   │       ├── planning.py
│   │       ├── router.py
│   │       ├── observation.py
│   │       ├── reasoning.py
│   │       └── decision.py
│   ├── api/
│   │   └── server.py             # FastAPI app, all routes
│   ├── tools/
│   │   ├── __init__.py           # Tool registration
│   │   ├── calculate_credit_risk.py
│   │   ├── analyze_cashflow_stability.py
│   │   ├── list_applicant_loans.py
│   │   └── assess_collateral.py
│   ├── tool_registry.py
│   ├── db.py                     # get_conn
│   ├── config.py                 # DBSettings, AgentSettings
│   └── applicants.py             # resolve_applicants_by_name
├── loan-ui/                      # React frontend
│   ├── src/
│   │   ├── App.tsx               # Main UI, API calls
│   │   ├── App.css
│   │   └── main.tsx
│   ├── index.html
│   ├── vite.config.ts
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
├── DB/
│   ├── init.sql/init.sql         # Schema + 10-applicant seed
│   └── seed_test_cases.sql      # Alice, Bob, Carol test cases
├── scripts/
│   └── run_seed.py               # Apply seed_test_cases.sql
├── docker-compose.yaml
├── Dockerfile.api
├── requirements.txt
├── .env.example
├── Architecture.md               # Original architecture notes
└── DEPLOY.md                     # Deployment guide
```

## Entry Points

| Entry | Command / Path |
|-------|----------------|
| API server | `uvicorn loan_agent.api.server:app --host 0.0.0.0 --port 8001` |
| UI dev | `npm run dev` (Vite, port 5173) |
| Full stack | `docker compose up -d` (from Loan_Agent) |
| Seed DB | `python scripts/run_seed.py` or mount `seed_test_cases.sql` in Postgres init |

## Key References

- [agent.md](agent.md) — Agent design
- [architecture.md](architecture.md) — System layout
- [tech_stack.md](tech_stack.md) — Dependencies
- [tools.md](tools.md) — Tool catalog
- [api_contracts.md](api_contracts.md) — API endpoints
- [data_models.md](data_models.md) — DB and schemas
- [execution_flow.md](execution_flow.md) — Control flow
