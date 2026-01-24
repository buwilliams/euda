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
- Route modules with prefixes:
  - `/api/jobs` — Job CRUD, assets, execution traces
  - `/api/agents` — Agent listing, state, identity, config, memory, monitoring
  - `/api/chat` — Chat with agents, conversation history
  - `/api/user` — User identity and long-term memory
  - `/api/auth` — Authentication check, login, logout
  - `/api/upload` — File uploads for processing
  - `/api/transcribe` — Audio transcription (speech-to-text)
  - `/api/synthesize` — Text-to-speech synthesis
  - `/api` — System routes (health, settings, costs, incidents, backups, SSE events)

## System Endpoints

- `GET /api/health` — Health check
- `GET /api/about` — About/pitch content
- `GET /api/daily-quote` — Personalized daily quote
- `GET /api/costs` — Cost summary (session, today, 7 days, month)
- `GET /api/costs/by-agent?days={n}` — Cost breakdown by agent
- `GET /api/settings` — LLM settings with providers and speech capabilities
- `PUT /api/settings/llm` — Update LLM provider, models, budget
- `PUT /api/settings/schedules` — Update schedule times
- `GET /api/incidents?agent_id={id}&days={n}` — List incidents
- `POST /api/incidents/{id}/acknowledge` — Acknowledge incident
- `POST /api/incidents/acknowledge-all?agent_id={id}` — Acknowledge all incidents
- `GET /api/events` — SSE endpoint for real-time updates

## Agent Management Endpoints

- `GET /api/agents` — List all agents
- `GET /api/agents/{id}` — Get agent details
- `GET /api/agents/{id}/state` — Get operational state with token usage
- `PATCH /api/agents/{id}/state` — Update state (enabled/disabled/paused)
- `GET /api/agents/{id}/identity` — Get agent identity (markdown)
- `PATCH /api/agents/{id}/identity` — Update agent identity
- `GET /api/agents/{id}/config` — Get agent configuration
- `PATCH /api/agents/{id}/config` — Update agent configuration
- `GET /api/agents/{id}/memory/short-term` — List short-term memory items
- `GET /api/agents/{id}/memory/short-term/{entry_id}` — Get single memory item
- `POST /api/agents/{id}/memory/short-term` — Add memory item
- `DELETE /api/agents/{id}/memory/short-term/{entry_id}` — Delete memory item
- `GET /api/agents/{id}/memory/long-term/dates` — List long-term memory dates
- `GET /api/agents/{id}/memory/long-term?date={date}` — Get long-term memory for date
- `POST /api/agents/{id}/memory/long-term` — Add long-term memory entry
- `GET /api/agents/{id}/completed-jobs?limit={n}` — Jobs completed by agent
- `GET /api/agents/{id}/monitoring?offset={n}&limit={n}` — Monitoring stats with pagination
- `GET /api/agents/{id}/logs/consolidation?days={n}` — Get consolidation logs
- `POST /api/agents/{id}/reflection/trigger` — Trigger consolidation (phase: append/consolidate/both)
- `GET /api/agents/{id}/active-executions` — Active trigger jobs for UI state

## Job Management Endpoints

- `GET /api/jobs` — List jobs with filters
- `POST /api/jobs` — Create job
- `GET /api/jobs/{id}` — Get job details
- `PATCH /api/jobs/{id}` — Update job
- `DELETE /api/jobs/{id}` — Delete job
- `POST /api/jobs/{id}/complete` — Complete job
- `POST /api/jobs/{id}/archive` — Archive job
- `POST /api/jobs/{id}/restore` — Restore completed job to todo
- `POST /api/jobs/{id}/unblock` — Remove blocking tags
- `POST /api/jobs/{id}/feedback` — Send feedback to agent
- `GET /api/jobs/{id}/children` — Get child jobs
- `GET /api/jobs/{id}/assets` — List job assets
- `GET /api/jobs/{id}/assets/{filename}` — Get asset content
- `POST /api/jobs/{id}/assets` — Upload asset
- `DELETE /api/jobs/{id}/assets/{filename}` — Delete asset
- `GET /api/jobs/{id}/trace?days={n}` — Full execution trace
- `GET /api/jobs/{id}/api-calls?days={n}` — API calls for job
- `GET /api/jobs/{id}/assignee` — Get assigned agent
- `POST /api/jobs/{id}/assign` — Assign agent to job
- `POST /api/jobs/{id}/unassign` — Remove agent from job

## Chat Endpoints

- `GET /api/chat?agent_id={id}` — Get current conversation
- `POST /api/chat` — Send message to agent
- `GET /api/chat/history?agent_id={id}&date={date}` — Get conversation history
- `GET /api/chat/conversations/recent?count={n}` — Recent conversations
- `POST /api/chat/conversations/fork` — Fork past conversation
- `DELETE /api/chat/conversations/{session_id}` — Delete conversation

## Speech Endpoints

- `GET /api/transcribe/status` — Check if STT available
- `POST /api/transcribe` — Transcribe audio to text
- `GET /api/synthesize/status` — Check if TTS available
- `POST /api/synthesize` — Synthesize text to speech

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
- Job is tagged with `background` for load-based pacing (see specs/1_agents.md)
- Chat uses `read_asset` to access file content
- For text files: extracts identity info and creates memories
- Returns: filename, job_id, size

Future integrations (email, calendar, social media, etc.) should follow this same pattern and include the `background` tag for pacing.

## Fresh Start & Backups

- `POST /api/fresh-start` — Reset all user data, create timestamped backup, preserve agent configs and identity templates
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
  - `consolidation:progress` — sent during consolidation execution with step, message, execution_id
  - `consolidation:llm_complete` — sent when consolidation LLM call completes, includes token counts
  - `consolidation:complete` — sent when consolidation phase finishes (append or consolidate)
  - `consolidation:error` — sent if consolidation encounters an error
- Consolidation events include `execution_id` for correlating UI triggers with backend progress
- Clients reconnect automatically on disconnect
- Graceful shutdown closes connections before server stops

## Storage

- Use flat files where simple storage is needed
- Use SQLite only where indexing and querying is required
- Jobs in SQLite (`data/jobs/db.sqlite`)
- Config, logs, state in JSON/JSONL files

## Package Management

- [uv](https://docs.astral.sh/uv/) is the only package manager
- Dependencies in `pyproject.toml`, lock in `uv.lock`
- Never use pip, requirements.txt, or manual virtualenvs

## Architecture

- The user is conceptually an agent with a different interface (web UI vs autonomous loop)
- Tools are the only way agents interact with the system
- Every LLM call includes rich context: agent identity, user identity, available tools, job context
- Self-hosted — users own their data and infrastructure
- The intelligence is separate from the interface — today web, tomorrow voice/wearable
