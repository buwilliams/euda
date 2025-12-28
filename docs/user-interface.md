# User Interface

*Current UI implementation and component reference*

Euno's interface is designed to surface what matters before you ask, guard your attention, and feel like a caring friend who knows you. This document describes the current implementation. For the vision and philosophy behind the design, see [user-experience.md](user-experience.md).

---

## Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                        app-container                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                         app                               │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              context-content                        │  │  │
│  │  │              (daily quote)                          │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              tabs-container                         │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │           tab-content                         │  │  │  │
│  │  │  │    (Chat / Focus / About / History)           │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │           tab-menu                            │  │  │  │
│  │  │  │   [💬 Chat] [☐ Focus 3] [ℹ About] [◷ History] │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              input-bar                              │  │  │
│  │  │   [What's on your mind?              ] [➤] [×]      │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Layout notes:**
- Single-column centered layout (max 640px)
- Off-white background (#f8f8f8) with white cards/inputs for contrast
- Tab-based navigation replaces side panels

---

## Components

### Context View

The top content area showing the daily quote.

```html
<div class="context-content">
    <!-- Daily quote loads here -->
</div>
```

**Daily Quote:**
- Fetched from `/api/quote` on load
- Displays inspirational quote with author
- Centered, italicized text

### Tab System

Four tabs provide the main navigation:

| Tab | Icon | Purpose |
|-----|------|---------|
| Chat | 💬 | Conversation with Euno |
| Focus | ☐ | Task and project management (Things-like) |
| About | ℹ | About page (docs/pitch.md content) |
| History | ◷ | Past conversation browser |

**Focus badge:** Shows count of tasks due today

### Input Bar

Bottom-anchored bar with text input and action buttons.

```
┌─────────────────────────────────────────────┐
│  ┌─────────────────────────────────┐ ┌──┐ ┌──┐ │
│  │ What's on your mind?            │ │➤│ │×│ │
│  └─────────────────────────────────┘ └──┘ └──┘ │
└─────────────────────────────────────────────┘
```

**Components:**
- **Text input** — Auto-expanding textarea with placeholder "What's on your mind?"
- **Send button** — Paper plane icon, black background (#333)
- **Clear button** — X icon, clears chat and creates new session

**Keyboard shortcuts:**
- Enter — Send message
- Shift+Enter — New line in message

---

## Tab Content

### Chat Tab

Conversation messages displayed inline.

```
┌─────────────────────────────────────────────┐
│                                    You      │
│          What should I focus on today?      │
│                    (white bubble, right)    │
├─────────────────────────────────────────────┤
│ Based on your energy levels and schedule,   │
│ I'd suggest starting with deep work...      │
│ (left-aligned, markdown rendered)           │
└─────────────────────────────────────────────┘
```

**Message Types:**
- `inline-message-you` — User messages (white background, right-aligned, subtle border)
- `inline-message-friend` — Assistant messages (left-aligned, markdown rendered)

**States:**
- Empty state with prompt to start conversation
- Shows thinking indicator while waiting for response

### Focus Tab

Things-like task management with slide navigation.

**Main Menu:**
```
┌──────────────────────────────────────┐
│  ☀️  Today                       3 → │
│  📅  Upcoming                    5 → │
│  ⏳  Anytime                    12 → │
│  💭  Someday                     8 → │
│  📖  Logbook                    24 → │
├──────────────────────────────────────┤
│  📁  General                     2 → │
│  📁  User Project                4 → │
│  ✨  Notifications               3 → │
│      from Euno                       │
│  ✨  Curator                     1 → │
│      from Euno                       │
└──────────────────────────────────────┘
```

**Timeline Categories:**
- **Today** — Tasks with due_date = today
- **Upcoming** — Tasks with due_date > today
- **Anytime** — Tasks with no due_date and someday = false
- **Someday** — Tasks with someday = true
- **Logbook** — Completed tasks

**Projects Section:**
- General project always first
- User-created projects in middle
- System projects (Notifications, Curator) last with ✨ icon and "from Euno" subtitle

**System Project Filtering:**
Tasks in Notifications and Curator projects are hidden from timeline views unless the user explicitly sets a "When" value. They always appear when viewing the project directly.

**Timeline View (after selecting):**
```
┌──────────────────────────────────────┐
│ ← Today                              │
├──────────────────────────────────────┤
│ Project Alpha                        │
│ ────────────────────────             │
│ ☐ Task name                          │
│   Task description preview...        │
│ ☐ Another task                       │
│                                      │
│ General                              │
│ ────────────────────────             │
│ ☐ General task                       │
└──────────────────────────────────────┘
```

Tasks are grouped by project within each timeline view.

**Task Card (Expanded):**
```
┌──────────────────────────────────────┐
│ ☐ Task Name                      [−] │
├──────────────────────────────────────┤
│ Full task description with all       │
│ details and context...               │
├──────────────────────────────────────┤
│ 📁 Project Name                      │
├──────────────────────────────────────┤
│ [When] [Archive] [Delete]            │
└──────────────────────────────────────┘
```

**When Picker:**
Accessible from expanded task card, allows scheduling:
- ☀️ Today — Set due_date to today
- 📅 Pick a date — Calendar date picker
- 💭 Someday — Set someday = true, clear due_date
- ✕ Clear — Remove all scheduling

### About Tab

Displays the product pitch from `docs/pitch.md`.

- Content loaded from `/api/about` endpoint
- Rendered as markdown
- Scrollable content area

### History Tab

Past conversation browser.

```
┌──────────────────────────────────────┐
│ 2025-12-27 14:30                     │
│ What should I focus...               │
├──────────────────────────────────────┤
│ 2025-12-27 09:15                     │
│ Good morning, I wanted to talk...    │
├──────────────────────────────────────┤
│ 2025-12-26 16:45                     │
│ Can you help me plan...              │
└──────────────────────────────────────┘
```

**List Items:**
- Date and time of conversation
- Preview of first message (truncated)
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
┌─────────────────────────────────────┐
│  document.pdf                  45%  │
│  ████████░░░░░░░░░░░░░░░░░░░░░░░   │
│  Uploading...                       │
└─────────────────────────────────────┘
```

**States:**
- Uploading with progress bar
- Processing (after upload completes)
- Success/failure message

### When Picker Modal

Bottom sheet for scheduling tasks/projects.

```
┌─────────────────────────────────────┐
│  (backdrop - tap to close)          │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  ☀️  Today                    │  │
│  │  📅  Pick a date...           │  │
│  │  💭  Someday                  │  │
│  │  ✕   Clear                    │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## Visual Style

**Typography:**
- Font: Roboto, system font stack fallback
- Black text on off-white background (#333 on #f8f8f8)
- Generous line height (1.6)

**Colors:**
- App background: #f8f8f8 (off-white)
- Cards/inputs: #fff (white, for contrast)
- Text: #333 (primary), #666 (secondary), #999 (muted)
- Borders: #e0e0e0 (standard), #e8e8e8 (subtle)
- Send button: #333 background, #fff icon

**Spacing:**
- Base unit: 0.5rem (8px)
- Content padding: 1.5rem
- Max content width: 640px

**Transitions:**
- Tab switches: instant
- Hover states: 0.15s
- Focus view navigation: 0.3s slide

---

## State Management

**Client-side state:**
```javascript
sessionId          // Current chat session UUID (localStorage)
activeTab          // 'chat' | 'focus' | 'about' | 'history'
focusView          // 'menu' | 'today' | 'upcoming' | 'anytime' | 'someday' | 'logbook' | 'project-{id}'
focusViewHistory   // Stack for back navigation
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
| Escape | Close picker/modal (if open) |

---

## File Structure

```
static/
├── index.html          # Single-page app (HTML + CSS + JS)
└── images/
    └── euno-logo-*.png # Logo variants
```

The UI is a single HTML file with embedded CSS and JavaScript. No build step required.
