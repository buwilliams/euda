# User Interface

*Current UI implementation and component reference*

This document describes the actual UI as implemented. For the vision and philosophy behind the design, see [user-experience.md](user-experience.md).

---

## Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                        app-container                            │
│  ┌─────────────────────────────────┐  ┌──────────────────────┐  │
│  │              app                │  │    panel (right)     │  │
│  │  ┌───────────────────────────┐  │  │                      │  │
│  │  │     context-content       │  │  │  Focus or History    │  │
│  │  │     (daily quote)         │  │  │                      │  │
│  │  └───────────────────────────┘  │  │                      │  │
│  │  ┌───────────────────────────┐  │  │                      │  │
│  │  │      inline-chat          │  │  │                      │  │
│  │  │   (conversation area)     │  │  │                      │  │
│  │  └───────────────────────────┘  │  │                      │  │
│  │  ┌───────────────────────────┐  │  │                      │  │
│  │  │       input-bar           │  │  │                      │  │
│  │  │  [Clear][Upload][Focus]   │  │  │                      │  │
│  │  │  [History]                │  │  │                      │  │
│  │  │  [Talk to me...    ][Send]│  │  │                      │  │
│  │  └───────────────────────────┘  │  │                      │  │
│  └─────────────────────────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Responsive behavior:**
- Desktop: Main content (max 640px) centered, panel (280px) slides in from right
- Panel open: Main content shrinks to 480px
- Mobile (<800px): Panel takes full width, main content hidden when panel open

---

## Components

### Context View

The main content area showing the daily quote and conversation.

```html
<section class="context-view">
    <div class="context-content">
        <!-- Daily quote loads here -->
    </div>
    <div class="inline-chat">
        <!-- Conversation messages appear here -->
    </div>
    <div class="input-bar">
        <!-- Menu buttons and text input -->
    </div>
</section>
```

**Daily Quote:**
- Fetched from `/api/quote` on load
- Displays inspirational quote with author
- Centered, italicized text

### Input Bar

Bottom-anchored bar with menu buttons and text input.

```
┌─────────────────────────────────────────────┐
│  [×Clear] [↑Upload] [☐Focus] [◷History]     │
│  ┌─────────────────────────────────┐ ┌────┐ │
│  │ Talk to me...                   │ │Send│ │
│  └─────────────────────────────────┘ └────┘ │
└─────────────────────────────────────────────┘
```

**Menu Buttons:**

| Button | Icon | Action |
|--------|------|--------|
| Clear | × | Clears chat UI, creates new session |
| Upload | ↑ | Opens file picker for inbox upload |
| Focus | ☐ | Toggles Focus panel (tasks/projects) |
| History | ◷ | Toggles History panel (past chats) |

**Text Input:**
- Auto-expanding textarea
- Placeholder: "Talk to me..."
- Send button or Enter to submit
- Shift+Enter for newlines

### Inline Chat

Conversation messages displayed inline above the input bar.

```
┌─────────────────────────────────────────────┐
│ You                                         │
│ What should I focus on today?               │
├─────────────────────────────────────────────┤
│ Based on your energy levels and schedule,   │
│ I'd suggest starting with deep work...      │
└─────────────────────────────────────────────┘
```

**Message Types:**
- `inline-message-you` — User messages (right-aligned implied by role)
- `inline-message-friend` — Assistant messages (markdown rendered)

**States:**
- Hidden by default (no conversation)
- Appears when first message sent
- Shows thinking indicator while waiting

---

## Side Panels

Right-side panels that slide in. Only one panel can be open at a time.

### Focus Panel

Task and project management.

```
┌──────────────────────────┐
│  FOCUS                   │
├──────────────────────────┤
│  ▼ Today            (3)  │
│  ────────────────────    │
│  ☐ Review PR #123        │
│  ☐ Call with Sarah       │
│  ☐ Write summary         │
├──────────────────────────┤
│  ▼ Projects         (2)  │
│  ────────────────────    │
│  📁 Website Redesign     │
│     ☐ Finalize mockups   │
│  📁 Q1 Planning          │
├──────────────────────────┤
│  ▶ Completed        (5)  │
│  (collapsed)             │
└──────────────────────────┘
```

**Sections:**
- **Today** — Tasks due today or unscheduled
- **Projects** — Active projects with their tasks
- **Completed** — Recently completed tasks (collapsed by default)

**Task Actions:**
- Click checkbox to complete/uncomplete
- Click task text to view full details
- Snooze button (💤) to defer to tomorrow
- Archive button (📦) to archive
- Delete button (×) to remove

**Badge:** Shows count of pending tasks for today

### History Panel

Past conversation browser.

```
┌──────────────────────────┐
│  HISTORY                 │
├──────────────────────────┤
│  2025-12-27 14:30        │
│  What should I focus...  │
├──────────────────────────┤
│  2025-12-27 09:15        │
│  Good morning, I wanted  │
│  to talk about...        │
├──────────────────────────┤
│  2025-12-26 16:45        │
│  Can you help me plan... │
└──────────────────────────┘
```

**List Items:**
- Date and time of conversation
- Preview of first message (2 lines max)
- Click to fork into new session

**Fork Behavior:**
- Creates new session with new ID
- Pre-populates agent context with old messages
- Loads messages into chat UI
- Original conversation preserved unchanged

---

## Overlays

### Upload Progress

Shows during file upload to inbox.

```
┌─────────────────────────────────┐
│  document.pdf            45%   │
│  ████████░░░░░░░░░░░░░░░░░░░   │
│  Uploading...                  │
└─────────────────────────────────┘
```

**States:**
- Uploading with progress bar
- Processing (after upload completes)
- Success/failure message

---

## Visual Style

**Typography:**
- System font stack (SF Pro, Segoe UI, etc.)
- Black text on white background (#333 on #fff)
- Generous line height (1.6)

**Colors:**
- Background: #fff (main), #fafafa (panels)
- Text: #333 (primary), #666 (secondary), #999 (muted)
- Borders: #eee (subtle), #ddd (stronger)
- Accent: #007AFF (links, buttons)

**Spacing:**
- Base unit: 0.5rem (8px)
- Content padding: 1.5rem
- Panel width: 280px
- Max content width: 640px (480px with panel)

**Transitions:**
- Panel slide: 0.3s ease
- Hover states: 0.15s
- Section collapse: 0.2s

---

## State Management

**Client-side state:**
```javascript
sessionId          // Current chat session UUID (localStorage)
activePanel        // 'tasks' | 'history' | null (localStorage)
tasksData          // Cached task list
projectsData       // Cached project list
historyData        // Cached conversation list
```

**Real-time updates:**
- SSE connection to `/api/events`
- Events: `tasks_update`, `projects_update`, `notification_update`
- Auto-reconnect on disconnect

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Send message |
| Shift+Enter | New line in message |
| Escape | Close panel (if open) |

---

## File Structure

```
static/
├── index.html          # Single-page app (HTML + CSS + JS)
└── images/
    └── euno-logo-*.png # Logo variants
```

The UI is a single HTML file with embedded CSS and JavaScript. No build step required.
