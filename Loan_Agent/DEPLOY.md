# Loan Agent – Deployment Guide

Deploy the Loan Agent MVP using Docker on AWS Lightsail, a generic VPS, or a PaaS.

---

## Quick Start (Local Docker)

```bash
cd Loan_Agent

# Copy env and add OPENAI_API_KEY
cp .env.example .env
# Edit .env: set OPENAI_API_KEY=sk-... (required for agent)

# Build and run (Postgres + API + UI)
docker compose up -d

# Optional: include pgAdmin for DB access
docker compose --profile tools up -d
```

- **UI**: http://localhost  
- **API**: http://localhost:8001  
- **pgAdmin** (if using `--profile tools`): http://localhost:5050  

---

## Docker Images

| Service | Image build | Port |
|---------|-------------|------|
| API     | `Dockerfile.api` (Python 3.12, FastAPI) | 8001 |
| UI      | `loan-ui/Dockerfile` (Vite build + nginx) | 80 |
| Postgres| `postgres:15` | 5432 |

The UI serves the React app and proxies `/api/*` to the API. No CORS configuration is needed in production.

---

## AWS Lightsail

### 1. Create instance

- Lightsail → Create instance
- Platform: **Linux/Unix**
- Blueprint: **OS only** (e.g. Ubuntu 22.04)
- Plan: **$3.50/mo** (512 MB) or **$5/mo** (1 GB recommended)

### 2. Install Docker

SSH into the instance:

```bash
sudo apt update && sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a/r/etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
# Log out and back in for docker group
```

### 3. Deploy

```bash
# Clone and enter project
git clone <your-repo-url> Agent007 && cd Agent007/Loan_Agent

# Create .env
cp .env.example .env
nano .env  # Add OPENAI_API_KEY=sk-..., optionally POSTGRES_PASSWORD

# Open Lightsail firewall (Networking tab)
# - Add HTTP (80) and HTTPS (443) if using a load balancer
# - Add custom 8001 if you want direct API access

# Build and run
docker compose up -d --build
```

### 4. Access

- **Public IP**: http://&lt;instance-public-ip&gt;  
- Static IP: Create one in Lightsail and attach it for a stable address.

---

## Other cheap hosting options

### Railway

1. Connect GitHub repo.
2. Add services: `api` (Dockerfile.api), `ui` (loan-ui/Dockerfile), `postgres` (Railway Postgres).
3. Set `LOAN_DB_*` from Postgres connection URL; add `OPENAI_API_KEY`.
4. For UI, use build arg `VITE_API_BASE` = Railway API URL (or put both behind Railway’s proxy).

### Render

- Backend: Web Service, Docker, `Dockerfile.api`.
- Frontend: Static Site or Web Service with `loan-ui/Dockerfile`.
- Postgres: Add Render Postgres; set `LOAN_DB_*` from its URL.
- Set `OPENAI_API_KEY` in env.

### Fly.io

```bash
fly launch
fly postgres create
fly secrets set OPENAI_API_KEY=sk-...
fly deploy
```

Use Fly’s `fly.toml` to define API and UI services and wire them to Postgres.

### DigitalOcean / Hetzner VPS

Same approach as Lightsail:

- Spin up Ubuntu droplet/server.
- Install Docker and Docker Compose.
- Clone repo, configure `.env`, run `docker compose up -d`.
- Open ports 80 and 8001 in the firewall.

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key (agent uses GPT) |
| `POSTGRES_PASSWORD` | No | `admin` | Postgres password |
| `LOAN_DB_HOST` | No* | `localhost` | DB host (compose sets to `postgres`) |
| `LOAN_DB_PORT` | No | `5432` | DB port |
| `LOAN_DB_NAME` | No | `loan_db` | DB name |
| `LOAN_DB_USER` | No | `admin` | DB user |
| `LOAN_DB_PASSWORD` | No | `admin` | DB password |
| `ENABLE_AUTONOMY` | No | `false` | Use autonomous ReAct agent |
| `AGENT_MAX_STEPS` | No | `8` | Max tool steps in autonomous mode |

\* In docker-compose, `LOAN_DB_HOST` is overridden to `postgres`.

---

## Troubleshooting

- **API can’t reach DB**: Ensure `postgres` is healthy before API starts; check `LOAN_DB_HOST=postgres`.
- **UI 502 / API not reachable**: Confirm API is up on port 8001 and UI nginx can resolve `api:8001`.
- **Agent fails**: Verify `OPENAI_API_KEY` is set and valid.
- **Rebuild after code changes**: `docker compose up -d --build`
