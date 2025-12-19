# Implementation Todo

Track user flows and features to implement.

## User Flows

### Push Flows (system initiates)

- [ ] **Morning Attention**
  - [ ] Generate morning briefing content
  - [ ] Show today's calendar events
  - [ ] Display surfaced opportunities
  - [ ] Show energy forecast
  - [ ] Include "one thing to look forward to"
  - [ ] Notification trigger (email/push)

- [ ] **Evening Journal**
  - [ ] Agent-generated reflection prompts based on the day
  - [ ] Warm, tired-friendly tone
  - [ ] Auto-save journal entry to log
  - [ ] Notification trigger

- [ ] **Weekly Review**
  - [ ] Patterns from the past week
  - [ ] Upcoming week preparation
  - [ ] Notification trigger

### Pull Flows (user initiates)

- [ ] **Chat Intent Detection**
  - [ ] Detect intent from message tone/content
  - [ ] Ask when uncertain: "Do you want me to help solve this, or just hear it?"
  - [ ] Adapt response mode:
    - [ ] Explore → participate, challenge, expand
    - [ ] Vent → listen, reflect, empathize
    - [ ] Capture → confirm, clarify, log
    - [ ] Decide → surface values, pros/cons
    - [ ] Brainstorm → generate, connect, play

- [ ] **Chat Ingestion**
  - [ ] Text capture: "I had a conversation with Sarah about X"
  - [ ] Auto-log conversations to life log
  - [ ] File upload support in web UI
  - [ ] URL fetching: "Read this article and log what's interesting"
  - [ ] Photo/image processing via chat

- [ ] **Log Browsing**
  - [ ] View entries by date
  - [ ] Search across logs
  - [ ] Filter by source/type

### Cards & Connection

- [ ] **Value Cards**
  - [ ] Generate internal card from values
  - [ ] Generate public card (user reviews/approves)
  - [ ] Edit public card via UI
  - [ ] Approve public card for sharing

- [ ] **Card Exchange**
  - [ ] Receive cards from others
  - [ ] View received cards
  - [ ] Update card status (reviewed, connected, declined)
  - [ ] REST endpoint for card exchange

### Discovery

- [ ] **World Agent Discovery**
  - [ ] Scheduled discovery sweeps
  - [ ] 90/10 aligned vs expansive balance
  - [ ] Surface opportunities in Today view
  - [ ] Mark opportunities as surfaced/responded

## Technical Infrastructure

- [ ] **Agent Manager**
  - [ ] Spawn and monitor all agents
  - [ ] Health checks and auto-restart
  - [ ] Scheduled triggers (morning, evening, weekly)

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
- [ ] Better markdown rendering
- [ ] Mobile responsive refinements
- [ ] Keyboard shortcuts

---

## Completed

- [x] Core agent pattern (context + loop + tools)
- [x] All 6 agents implemented (Ingestion, Interaction, Summary, Values, Attention, World)
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
