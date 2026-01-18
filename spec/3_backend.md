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
  - `/api/agents` — Agent listing and management
  - `/api/chat` — Chat with agents
  - `/api/user` — Profile and long-term memory
  - `/api/auth` — Authentication
  - `/api/upload` — File uploads with identity extraction
  - `/api/events` — SSE endpoint
  - `/api/transcribe` — Audio transcription (speech-to-text)
  - `/api/synthesize` — Text-to-speech synthesis
  - `/api/rate-limiting` — Rate limiter status and control
  - `/api/fresh-start` — Reset user data with backup
  - `/api/backups` — Backup management

## Agent Management Endpoints

- `GET /api/agents/{id}/profile` — Get agent profile (markdown)
- `PATCH /api/agents/{id}/profile` — Update agent profile
- `GET /api/agents/{id}/config` — Get agent configuration
- `PATCH /api/agents/{id}/config` — Update agent configuration
- `GET /api/agents/{id}/memory/short-term` — List short-term memory items
- `POST /api/agents/{id}/memory/short-term` — Add memory item
- `DELETE /api/agents/{id}/memory/short-term/{entry_id}` — Delete memory item
- `GET /api/agents/{id}/memory/long-term/dates` — List long-term memory dates
- `GET /api/agents/{id}/memory/long-term?date={date}` — Get long-term memory for date
- `GET /api/agents/{id}/monitoring` — Get monitoring stats and recent prompts
- `GET /api/agents/{id}/logs/reflection?days={n}` — Get reflection logs
- `POST /api/agents/{id}/reflection/trigger` — Manually trigger reflection, returns execution_id
- `POST /api/agents/{id}/exploration/trigger` — Manually trigger exploration, returns execution_id

## Integrations

Integrations bring external data into Euno. All integrations follow the same pattern:

1. **Create a job** — The integration creates a job assigned to an agent (usually Chat)
2. **Store content as job assets** — Files/data are saved to `data/jobs/assets/{job-id}/`
3. **Agent processes asynchronously** — The assigned agent handles the job using its tools
4. **Results in memory** — Analysis and insights are stored in user's memory

This pattern ensures:
- Non-blocking operation (UI returns immediately)
- Visibility into what's being processed (jobs appear in queue)
- Consistent data storage (job assets)
- Agent autonomy in how to process content

### Upload Endpoint (File Integration)

- `POST /api/upload` — Upload file for agent processing
- Creates a job assigned to Chat agent with file as job asset
- Chat uses `read_asset` to access file content
- For text files: extracts identity info and creates memories
- Returns: filename, job_id, size

Future integrations (email, calendar, social media, etc.) should follow this same pattern.

## Fresh Start & Backups

- `POST /api/fresh-start` — Reset all user data, create timestamped backup, preserve agent configs and profile templates
- `GET /api/backups` — List all available backups with timestamps
- `POST /api/backups/restore` — Restore from a backup (current data backed up first)
- `DELETE /api/backups/{backup_name}` — Permanently delete a backup
- Backups use timestamped directory names: `data_backup-YYYYMMDD-HHMMSS`

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
- Event types:
  - `init` — sent on connection with initial job list
  - `ping` — keepalive every 30 seconds
  - `jobs_update` — sent when any job changes, includes full job list
  - `chat_update` — sent when chat messages are added
  - `agent_message` — sent via notifications tool for agent-to-user messages
  - `tts_audio` — sent when TTS audio is generated, includes base64 audio
  - `reflection:progress` — sent during reflection execution with step, message, execution_id
  - `reflection:llm_complete` — sent when reflection LLM call completes, includes token counts
  - `reflection:complete` — sent when reflection phase finishes (append or consolidate)
  - `reflection:error` — sent if reflection encounters an error
- Reflection events include `execution_id` for correlating UI triggers with backend progress
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
- Every LLM call includes rich context: agent identity, user identity, available tools, job context
- Self-hosted — users own their data and infrastructure
- The intelligence is separate from the interface — today web, tomorrow voice/wearable
