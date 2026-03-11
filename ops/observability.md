# Observability

Current observability capabilities and gaps for the Loan Agent MVP.

## Logging

### Implementation

- **Backend**: `logging.getLogger(__name__)` in agent nodes and server
- **Checkpoints**: State machine and nodes log at key steps:
  - Intent (checkpoint: stopping for clarification)
  - Planning
  - Router (tool selection)
  - Observation (tool result)
  - Reasoning
  - Decision

### Format

- Plain text to stdout
- No structured (JSON) logging
- No log levels explicitly controlled; defaults apply

### Gaps

- No correlation ID propagation (request → tool calls → logs)
- No request/response logging middleware
- No DB query timing logs
- No centralized log aggregation

## Health Checks

### Implementation

- **API**: `GET /health` returns `{ "status": "ok" }`
- **Docker**: Postgres service has healthcheck:
  - `pg_isready -U admin -d loan_db`
  - Interval 5s, timeout 5s, retries 5

### Gaps

- Health endpoint does not verify DB connectivity
- No readiness vs liveness distinction
- UI container has no health endpoint (nginx default)

## Metrics

### Current State

- No metrics exposed (Prometheus, StatsD, etc.)
- No request latency histograms
- No tool call counts or success/failure rates
- No agent run duration tracking

### Suggested

- Tool invocation count, latency, error rate per tool
- Agent run count by mode (deterministic vs autonomous)
- Clarification and chat session counts

## Tracing

### Current State

- No distributed tracing (OpenTelemetry, Jaeger, etc.)
- Agent trace (`ctx.trace`) is in-memory only; returned in API response for UI display
- No cross-service trace propagation

### Suggested

- Trace ID on incoming requests
- Propagate to tool calls and LLM calls
- Optional: persist agent_runs to DB for audit

## Deployment Context

- **Docker Compose**: Logs from api, ui, postgres go to stdout; `docker compose logs -f` for follow
- **Production**: Redirect stdout to log driver or aggregator (e.g. CloudWatch, ELK)

## Startup Logging

- API startup prints agent mode: `Loan Agent API: mode=autonomous|deterministic (ENABLE_AUTONOMY=...)`
