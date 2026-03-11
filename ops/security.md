# Security

Security posture of the Loan Agent MVP.

## Authentication

### Current State

- **API**: No authentication. All endpoints are unauthenticated.
- **UI**: No login; client talks to API directly.
- **DEPLOY.md**: Notes that production should add auth (JWT, mTLS, API gateway) but does not implement it.

### Recommendations

- Add API key or JWT for production deployments
- Restrict admin/tool endpoints if they are exposed
- Use HTTPS in production (Lightsail/load balancer termination)

## Authorization

- No role-based access control
- No per-applicant or per-resource authorization checks
- Any client can query any applicant or run any tool

## CORS

- Allowed origins: `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:5174`, `http://127.0.0.1:5174`
- Credentials allowed; all methods and headers allowed
- Production deployment behind nginx proxy: browser requests are same-origin (/api), so CORS from API is less relevant

**Recommendation**: Make CORS configurable via env (e.g. `CORS_ORIGINS`) for production domains.

## Secrets Management

### Current State

- `OPENAI_API_KEY`: Loaded from `.env` via python-dotenv
- `LOAN_DB_*`, `POSTGRES_PASSWORD`: From `.env` or docker-compose env
- No hardcoded secrets in code
- `.env` excluded from git (typical); `.env.example` has placeholders

### Recommendations

- Never commit `.env` to version control
- Use secret managers (AWS Secrets Manager, Vault) in production
- Rotate API keys periodically

## Data Exposure

### Agent Guardrails (from Project-plan/Agent.md)

- Agent should not expose raw transaction data, full credit history, or customer identifiers in outputs
- Current implementation: Tools return structured summaries (risk levels, recommendations, counts); no raw rows in agent response
- LLM prompts instruct to use only provided tool outputs and not invent numbers

### Database

- Postgres not exposed externally in default docker-compose (port 5432 bound to host for dev)
- Production: Restrict DB access to API container only; no public port

## Input Validation

- **API**: Pydantic models validate request bodies (UUIDs, numeric ranges)
- **Tools**: Validate applicant_id, loan_id as UUID; months 1–24; threshold_ratio > 0
- Invalid input returns 400 with error detail

## Rate Limiting

- No rate limiting on API
- OpenAI usage is only constrained by API key quota and cost

**Recommendation**: Add rate limiting for production (per-IP or per-token) to reduce abuse and cost spikes.

## Session Storage

- Clarification and chat sessions stored in-memory (`_session_store`, `_chat_session_store`)
- No persistence; sessions lost on restart
- No encryption; session_id is UUID (not guessable but not signed)

**Recommendation**: For production, use Redis or DB for session storage; consider signed session tokens.

## Dependency Security

- No known automated dependency scanning (e.g. Snyk, Dependabot) configured
- `npm audit` may report vulnerabilities in loan-ui; address before production
