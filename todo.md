# Implementation Todo

Track user flows and features to implement.

---

## Demo Priority (Critical Path)

### P0 - Agent Verification ✓

- [x] **Verify end-to-end flow works**
  - [x] Test: Drop file in inbox → Ingestion Agent processes → Log entry created
  - [x] Test: Chat with Interaction Agent → Intent detection → Response
  - [x] Test: Manager starts all agents without errors
  - [x] Test: Web UI loads and connects to API

- [x] **Fix Agent Status endpoint**
  - [x] Connect to actual agent state files instead of hardcoded response
  - [x] Show real status and last active timestamps

**Bugs Fixed:**
- [x] Agent process() now accumulates text from responses with tool calls
- [x] list_pending_files() now shows full paths for file tools

### P1 - New UI/UX ✓

- [x] **Design new minimal UI**
  - [x] Document UI principles in design.md
  - [x] Black text, white background, typography-first
  - [x] Avoid containers, borders, boxes
  - [x] Hide secondary features in navigation
  - [x] Dashboard shows only what matters NOW ("Freedom." when empty)

- [x] **Build new UI**
  - [x] Replace current index.html with minimal design
  - [x] Add logo (static/images/meandus.png)
  - [x] Chat as primary interface
  - [x] Attention items when pushed content exists
  - [x] Hidden navigation for Logs, Values, World, Agents

---

## User Flows

### Push Flows (system initiates)

- [ ] **Morning Attention**
  - [x] Generate morning briefing content
  - [ ] Show today's calendar events
  - [x] Display surfaced opportunities
  - [x] Show energy forecast
  - [x] Include "one thing to look forward to"
  - [ ] Notification trigger (email/push)

- [ ] **Evening Journal**
  - [x] Agent-generated reflection prompts based on the day
  - [x] Warm, tired-friendly tone
  - [x] Auto-save journal entry to log
  - [ ] Notification trigger

- [ ] **Weekly Review**
  - [ ] Patterns from the past week
  - [ ] Upcoming week preparation
  - [ ] Notification trigger

### Pull Flows (user initiates)

- [x] **Chat Intent Detection**
  - [x] Detect intent from message tone/content
  - [x] Ask when uncertain: "Do you want me to help solve this, or just hear it?"
  - [x] Adapt response mode:
    - [x] Explore → participate, challenge, expand
    - [x] Vent → listen, reflect, empathize
    - [x] Capture → confirm, clarify, log
    - [x] Decide → surface values, pros/cons
    - [x] Brainstorm → generate, connect, play

- [ ] **Chat Ingestion**
  - [x] Text capture: "I had a conversation with Sarah about X"
  - [x] Auto-log conversations to life log
  - [ ] File upload support in web UI
  - [ ] URL fetching: "Read this article and log what's interesting"
  - [ ] Photo/image processing via chat

- [x] **Log Browsing**
  - [x] View entries by date
  - [x] Search across logs
  - [ ] Filter by source/type

### Cards & Connection

- [ ] **Value Cards**
  - [x] Generate internal card from values
  - [x] Generate public card (user reviews/approves)
  - [ ] Edit public card via UI
  - [x] Approve public card for sharing

- [ ] **Card Exchange**
  - [x] Receive cards from others
  - [x] View received cards
  - [x] Update card status (reviewed, connected, declined)
  - [ ] REST endpoint for card exchange

### Discovery

- [x] **World Agent Discovery**
  - [x] Scheduled discovery sweeps
  - [x] 90/10 aligned vs expansive balance
  - [x] Surface opportunities in Today view
  - [x] Mark opportunities as surfaced/responded

## Technical Infrastructure

- [x] **Agent Manager**
  - [x] Spawn and monitor all agents
  - [x] Health checks and auto-restart
  - [x] Scheduled triggers (morning, evening, weekly)

- [ ] **Notifications**
  - [ ] Email notifications
  - [ ] Push notifications (web/mobile)

- [ ] **File Processing**
  - [ ] Image OCR/description
  - [ ] PDF text extraction
  - [ ] Audio transcription
  - [ ] Video processing

- [ ] **External Integrations**
  - [ ] Calendar API (Google/Apple)
  - [ ] URL content fetching

## UI Improvements

- [ ] Theme system (user customizable)
- [ ] File upload in chat
- [x] Better markdown rendering
- [ ] Mobile responsive refinements
- [ ] Keyboard shortcuts

---

## Completed

- [x] Core agent pattern (context + loop + tools)
- [x] All 6 agents implemented (Ingestion, Interaction, Summary, Values, Attention, World)
- [x] Worker Agent (The Executor) for task execution
- [x] Autonomous agent base class with signal-based communication
- [x] Log tools (write, read, search)
- [x] File processing tools (inbox watching)
- [x] Summary tools
- [x] Values tools (current, phase, lifetime)
- [x] Attention tools (energy, queue)
- [x] World tools (opportunities)
- [x] Cards tools (internal, public, received)
- [x] FastAPI web server
- [x] Web UI with all spec sections (Today, Chat, Journal, Review, Cards, Logs, Agents, Settings)
- [x] Markdown rendering in UI
- [x] Agent Manager with file watchers
- [x] Signal-based inter-agent communication
