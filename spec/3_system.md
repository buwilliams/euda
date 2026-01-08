# System

Rules for how the system operates and components interact.

- The user is conceptually an agent with a different interface (web UI vs autonomous loop)
- Tools are the only way agents interact with the system
- Every LLM call includes rich context: agent persona, user profile, memory, job context, conversation history
- Agents poll for actionable jobs — `poll_interval` in system config controls frequency (default 30s)
- Each agent runs in its own thread — one agent's work cannot block another
- Agents work autonomously but surface their work for user review
- Real-time updates to the UI via Server-Sent Events, not polling
- Single-page web application communicates via REST API
- Use flat files where simple storage is needed
- Use SQLite only where indexing and querying is required
- Agents initiate proactively, not just respond when asked
- Self-hosted — users own their data and infrastructure
- The intelligence is separate from the interface — today a web app, tomorrow voice, wearable, or ambient
- `system:start` creates trigger jobs at startup for subscribed agents
- Missed `time:morning` and `time:evening` triggers are detected at startup and create trigger jobs
- Disabled agents never receive trigger jobs or process any jobs
- Agent run state is tracked in `data/agents/{id}/state.json` with `last_ran` timestamp
- System trigger state is tracked in `data/system/state.json`
