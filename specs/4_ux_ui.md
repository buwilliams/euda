# UX & UI

Rules for user experience and user interface. The interface should feel like walking into a room where someone has already laid out what you need.

## User Experience

- Ambient and anticipatory — surface what matters before the user asks
- The interface answers "What do I need to know right now?" before any interaction
- Don't make the user think — the interface should be immediately obvious
- Don't make the user work — if the system can do something for the user, it should
- Instant feedback — actions happen immediately with no confirm dialogs, modals, or toasts
- Smart defaults — auto-generate what can be inferred (filenames, timestamps, relationships)
- Progressive disclosure — show the minimum UI needed, expand on demand
- Guard the user's attention — batch and summarize, don't interrupt unless it matters
- Less screen time without losing touch — curate, don't overwhelm
- Chat is for depth — thinking through complex things, not commands
- No engagement metrics, no ad revenue, no analytics tracking

## User Interface

- Single-column centered layout, mobile-first
- No build step required — vanilla HTML, CSS, JavaScript
- Consistent learnable navigation — patterns work the same way everywhere
- Stacked navigation with back buttons, not nested tabs or modals within modals
- Slide animations for spatial continuity — forward goes right, back goes left
- Swipe gestures for quick actions on mobile and desktop
- Chat expands in place — no jarring screen transitions between context and conversation
- Agent Manage view uses sub-views: Identity, Config, Memory, Monitoring — each stacks forward with back button
- Action buttons show running state during async operations (spinning icon, disabled siblings)

## Navigation Structure

Main tabs (bottom of screen):
- **Topics** — Primary work queue and topic management
- **Chat** — Conversation with agents
- **Focus** — Agent management and monitoring (formerly "Agents")
- **User** — User identity and memory
- **Settings** — LLM provider, budget, schedules, system config

## Topics Tab

- Hierarchical topic list with nested children
- Status indicators: todo (default), working (in progress), done, error, archived
- Inline completion actions (complete, archive, delete)
- Topic detail view with:
  - Description editing
  - Tags and assignee
  - Assets panel (files attached to topic)
  - Execution trace (logs + API calls)
  - Child topics

## Chat Tab

- Active conversation with selected agent (default: Chat agent)
- Voice input/output when provider supports it
- History access to past conversations
- Fork conversation to continue from a past point

## Focus Tab (Agent Management)

Agent list with sub-views accessible via stacked navigation:
- **Identity** — Markdown identity file, editable
- **Config** — Triggers, tools, consolidation settings
- **Memory** — Short-term and long-term memory browsing
- **Monitoring** — Recent LLM calls with token counts and timing
- **Incidents** — Threshold breaches and warnings
- **Consolidation Logs** — History of consolidation runs

Pause banner shown when agent is paused (with resume button).
Trigger buttons for manual consolidation (append/consolidate/both).

## User Tab

- User identity editing (markdown)
- Short-term memory list with add/delete
- Long-term memory browser by date

## Settings Tab

Collapsible sections:
- **LLM Provider** — Select provider, view model
- **Budget** — Monthly spending limit
- **Schedules** — Morning/evening trigger times
- **Fresh Start** — Reset all data with backup
- **Backups** — List and restore previous states

## Real-Time Updates

SSE connection provides live updates:
- Topic status changes refresh topic list
- Chat messages stream incrementally
- Consolidation progress shows in Focus tab
- Agent pause/resume events update UI immediately

## Testing

### E2E Testing with Playwright

Euno uses Playwright for end-to-end UI testing. Tests run in headless Chromium by default.

### data-testid Conventions

All interactive elements use `data-testid` attributes for reliable test selectors.

Naming:
- **Tabs:** `tab-{name}`, `tab-btn-{name}`
- **Buttons:** `{action}-btn` (e.g., `send-btn`, `pause-btn`)
- **Inputs:** `{field-name}` (e.g., `context-input`, `budget-limit`)
- **Containers:** `{component}-content` or `{component}-container`
- **Cards:** `{type}-card` (e.g., `topic-card`, `agent-card`)
- **Messages:** `message-{role}` (e.g., `message-user`, `message-agent`)
- **Menu items:** `menu-{name}` or `overflow-{name}`

### Running Tests

```bash
uv run pytest tests/e2e/ -v              # Headless (default)
uv run pytest tests/e2e/ -v --headed     # With browser visible
uv run pytest tests/e2e/ -v --headed --slowmo=500  # Slow for debugging
```
