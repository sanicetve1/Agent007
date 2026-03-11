# Technology Stack

## Backend

| Component | Version / Choice |
|-----------|------------------|
| Language | Python 3.12 |
| Web framework | FastAPI |
| ASGI server | Uvicorn |
| Database driver | psycopg (v3, binary) |
| LLM | OpenAI API (Responses API) |
| Config | python-dotenv |

### Key Dependencies (`requirements.txt`)

```
psycopg[binary]>=3.2.0
python-dotenv>=1.0.1
openai>=1.12.0
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
```

## Frontend

| Component | Version / Choice |
|-----------|------------------|
| Framework | React 18 |
| Build tool | Vite 5 |
| Language | TypeScript |
| Styling | CSS (custom) |

### Key Dependencies (`loan-ui/package.json`)

- `react`, `react-dom` ^18.3.1
- `vite` ^5.4.0
- `@vitejs/plugin-react-swc` ^3.7.0
- `typescript` ^5.5.0

## Database

| Component | Version |
|-----------|---------|
| Database | PostgreSQL 15 |
| Schema | `DB/init.sql/init.sql` |
| Seed | `DB/seed_test_cases.sql` (via docker volume) |

## Deployment

| Component | Choice |
|-----------|--------|
| Containers | Docker |
| Orchestration | Docker Compose |
| Web server (UI) | nginx (Alpine) |
| Base images | `python:3.12-slim`, `node:20-alpine`, `nginx:alpine`, `postgres:15` |

## Entry Points

- **API**: `uvicorn loan_agent.api.server:app --host 0.0.0.0 --port 8001`
- **UI**: nginx serving `/usr/share/nginx/html`, proxying `/api/` to `http://api:8001/`
