# Implementation Todo

Keep a simple list: todo and done. Only use one level, not nested todos.

## Todo
- [ ] Ingestion: video handler (ffprobe metadata, keyframes)
- [ ] Ingestion: audio handler (duration, ID3, chunked Whisper prep)
- [ ] Ingestion: mbox parser (stream messages, headers, threads)
- [ ] Ingestion: archive handler (list contents, safe extraction)
- [ ] Ingestion: tiered model selection (Haiku/Sonnet/Vision)
- [ ] Attention: project awareness (deadlines, rollover trigger)
- [ ] Interaction: the responses should be short (default 1 paragraph) unless it is asked to expand
- [ ] Interaction: Integrate proactive surfacing into UI
- [ ] Edit public value card via UI
- [ ] REST endpoint for card exchange
- [ ] Calendar API (Google/Apple)

## Completed

- [x] Ingestion: batch processing mode for faster ingestion (`--batch` flag, ~10x fewer API calls)
- [x] Ingestion: stable start/stop/resume with state tracking and crash recovery
- [x] Ingestion: status tools for Introspection agent (session stats, lifetime totals, history)
- [x] Ingestion: CLI batch runner with progress display (`python main.py ingest`)
- [x] Ingestion: External directory support with manifest tracking (`python main.py ingest /path -r`)
- [x] Ingestion: file classifier with magic byte detection (python-magic)
- [x] Ingestion: digest generator (metadata extraction per file type)
- [x] Ingestion: token budget manager with configurable daily limits
- [x] Ingestion: priority queue with relevance scoring
- [x] Ingestion: duplicate detection via SHA256 content hashing
- [x] Ingestion: large PDF handler (page-by-page, TOC extraction)
- [x] Ingestion: ignore patterns (system files, caches, temp files)
- [x] Ingestion: handler framework (text, image, PDF handlers)
- [x] Project and task management system
- [x] Project CRUD operations (create, read, update, archive)
- [x] Task queue with delegation logic
- [x] Daily views and quick tasks
- [x] Results storage
- [x] Rollover processing
- [x] Delegation decision tree (autonomous, approval, user-only, learning)
- [x] API endpoints for projects, tasks, and results
- [x] Chat integration - task/project tools in Interaction Agent
- [x] Frontend hints updated: "tasks today", "my projects", "create task", "results"
- [x] Notification system for agent-to-user proactive messaging
- [x] Notification queue (queue_notification, get_pending, mark_seen, dismiss)
- [x] API endpoints for notifications
- [x] Frontend polling and display with clickable action prompts
- [x] Agent identity evolution system
- [x] Agents can read their identity
- [x] Agents can propose restructured identities (not just append)
- [x] Approval workflow for identity changes
- [x] CLI command: python main.py evolve
- [x] URL fetching: "Read this article and log what's interesting"
- [x] Render markdown in chat (bold, italic, lists, headers, code blocks)
- [x] Auto-log conversations to the life log
- [x] Verify end-to-end flow works (inbox → ingestion → logs, chat → intent → response)
- [x] Fix Agent Status endpoint to read real state files
- [x] Fix agent process() to accumulate text from responses with tool calls
- [x] Fix list_pending_files() to show full paths
- [x] Design and build new minimal UI (black text, white background, typography-first)
- [x] Chat as primary interface with activity feed
- [x] Add logo and loading states
- [x] Evolution Agent (The Evolver) - formerly Introspection Agent
- [x] Identity file: data/shared/state/identity/evolution.identity.md
- [x] Tools: src/tools/evolution/ (agent/code analysis, capability docs)
- [x] Agent: src/agents/evolution.py (30-min autonomous loop)
- [x] Outputs: data/evolution/state/output/
- [x] Interaction Agent can access capabilities (user asks "what can you do?")
