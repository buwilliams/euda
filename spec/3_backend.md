# Backend

Rules for the server, API, and infrastructure.

## Web Server

- FastAPI application on port 8000
- Uvicorn ASGI server
- CORS enabled for all origins (local development)
- Static files served from `/static`
- Single-page app at root (`/`)

## Routes

- Routes organized in `src/web/routes/`
- Each route module has its own `router` with prefix:
  - `/api/jobs` — Job CRUD
  - `/api/agents` — Agent listing
  - `/api/chat` — Chat with agents
  - `/api/user` — Profile and lifelog
  - `/api/auth` — Authentication
  - `/api/upload` — File uploads
  - `/api/events` — SSE endpoint

## Authentication

- Optional password-based authentication
- Password stored as bcrypt hash in `data/system/auth.json`
- Session tokens stored in memory (cleared on restart)
- Public paths exempt: `/`, `/api/auth/check`, `/api/auth/login`, `/api/health`
- Static files exempt from auth
- If no password set, all routes accessible

## Server-Sent Events (SSE)

- Single SSE endpoint at `/api/events`
- Real-time updates for jobs, notifications, agent activity
- Event types: job_created, job_updated, job_completed, notification, agent_working
- Clients reconnect automatically on disconnect
- Graceful shutdown closes connections before server stops

## Storage

- Use flat files where simple storage is needed
- Use SQLite only where indexing and querying is required
- Jobs in SQLite (`data/jobs/db.sqlite`)
- Config, logs, state in JSON/JSONL files

## Architecture

- The user is conceptually an agent with a different interface (web UI vs autonomous loop)
- Tools are the only way agents interact with the system
- Every LLM call includes rich context: agent persona, user profile, memory, job context
- Self-hosted — users own their data and infrastructure
- The intelligence is separate from the interface — today web, tomorrow voice/wearable
