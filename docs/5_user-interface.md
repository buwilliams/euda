# User Interface

*Current UI implementation and component reference*

Euno's interface is designed to surface what matters before you ask, guard your attention, and feel like a caring friend who knows you. This document describes the current implementation. For the vision and philosophy behind the design, see [4_user-experience.md](4_user-experience.md).

---

## Splash Screen

On app load, an animated splash screen displays before the main UI:

```
┌─────────────────────────────────────────┐
│                                         │
│                                         │
│              E u n o                    │
│           (letters fade in)             │
│                                         │
│            "you-know"                   │
│   A personal intelligence that          │
│   learns to anticipate you              │
│                                         │
│                                         │
└─────────────────────────────────────────┘
```

**Animation sequence:**
1. Letters "E", "u", "n", "o" fade in one at a time (150ms each)
2. Pause (500ms)
3. Pronunciation and tagline fade in (400ms)
4. Hold (800ms)
5. Crossfade to login modal or main app

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
| About | ℹ | About page (docs/1_pitch.md content) |
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
├──────────────────────────────────────┤
│  📁  2026 Goal Setting           4 → │
│  📁  User Project                2 → │
├──────────────────────────────────────┤
│  ✓   Completed Jobs             12 → │
└──────────────────────────────────────┘
```

**Timeline Categories:**
- **Today** — Jobs with due_date = today
- **Upcoming** — Jobs with due_date > today
- **Anytime** — Jobs with no due_date and someday = false
- **Someday** — Jobs with someday = true

**Completed Jobs:**
- Shows root-level completed jobs (hierarchical navigation)
- Root = no parent OR parent is still active (not in completed list)
- Each completed job shows count of completed children
- Navigate into completed jobs to see their completed children
- Completed job detail view uses same UI as active jobs with "Restore" action

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

**Job Detail View:**
```
┌──────────────────────────────────────┐
│ ← Job Name                           │
├──────────────────────────────────────┤
│ [📅 When] [✓ Complete] [📦 Archive] [🗑 Delete] │
├──────────────────────────────────────┤
│ Name                                 │
│ Click to edit job name...            │
├──────────────────────────────────────┤
│ Description                          │
│ Markdown rendered, click to edit...  │
├──────────────────────────────────────┤
│ Child Jobs (3)                       │
│ ☐ Child job 1                    → │
│ ☐ Child job 2                    → │
│ [Add child job...              ] [+] │
├──────────────────────────────────────┤
│ Completed (2)                        │
│ ☑ Completed child 1              → │
│ ☑ Completed child 2              → │
├──────────────────────────────────────┤
│ 📎 Assets                        3 → │
└──────────────────────────────────────┘
```

**Completed Job Detail View:**
```
┌──────────────────────────────────────┐
│ ← Job Name                           │
├──────────────────────────────────────┤
│ [↩ Restore] [🗑 Delete]              │
├──────────────────────────────────────┤
│ ✓ Completed Yesterday                │
├──────────────────────────────────────┤
│ Name                                 │
│ Click to edit job name...            │
├──────────────────────────────────────┤
│ Description                          │
│ Markdown rendered, click to edit...  │
├──────────────────────────────────────┤
│ Completed Children (2)               │
│ ☑ Completed child 1              → │
│ ☑ Completed child 2              → │
├──────────────────────────────────────┤
│ 📎 Assets                        3 → │
└──────────────────────────────────────┘
```

Same UI as active jobs but with:
- "Restore" action instead of "Complete/Archive/When"
- Completed date badge at top
- Name and description still editable

**Assets View:**
- Upload files or create new text/markdown assets
- Text/markdown files are clickable and render inline
- Click to edit, with save/cancel controls
- Binary files show filename and size only
- Works for both active and completed jobs

**When Picker:**
Accessible from expanded task card, allows scheduling:
- ☀️ Today — Set due_date to today
- 📅 Pick a date — Calendar date picker
- 💭 Someday — Set someday = true, clear due_date
- ✕ Clear — Remove all scheduling

### About Tab

Displays the product pitch from `docs/1_pitch.md`.

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
- Hover states: 0.15s ease

**Animations:**

All navigation uses slide animations for spatial continuity:

| Navigation | Direction | Duration |
|------------|-----------|----------|
| Tab switch (forward) | Slide left | 0.3s |
| Tab switch (backward) | Slide right | 0.3s |
| Focus view deeper | Slide left | 0.3s |
| Focus view back | Slide right | 0.3s |
| History view deeper | Slide left | 0.3s |
| History view back | Slide right | 0.3s |

Tab order for direction: Chat (0) → Focus (1) → About (2) → History (3)

Switching from Chat to Focus slides left; Focus to Chat slides right.

---

## State Management

**Client-side state:**
```javascript
sessionId          // Current chat session UUID (localStorage)
activeTab          // 'chat' | 'focus' | 'about' | 'history'
previousTab        // Previous tab for animation direction
focusView          // 'menu' | 'today' | 'upcoming' | 'anytime' | 'someday' | 'completed' | 'job-{id}' | 'completed-{id}' | 'assets-{id}' | 'asset-{id}-{filename}'
focusViewHistory   // Stack for back navigation
historyView        // 'list' | 'detail'
jobsData           // Cached active jobs
completedJobsData  // Cached completed jobs
jobAssetsCache     // Cached assets per job
editingJobField    // {jobId, field} when editing a job field
currentAssetData   // Currently loaded asset content
editingAssetFilename // Asset being edited
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
├── index.html          # Main HTML shell
├── css/
│   └── app.css         # All styles
├── js/
│   ├── init.js         # App initialization and routing
│   ├── state.js        # Global state management
│   ├── splash.js       # Splash screen animation
│   ├── auth.js         # Authentication and login modal
│   ├── tabs.js         # Tab navigation with animations
│   ├── chat.js         # Chat tab functionality
│   ├── focus.js        # Focus tab (tasks/projects)
│   ├── history.js      # History tab
│   ├── about.js        # About tab
│   ├── upload.js       # File upload handling
│   └── utils.js        # Shared utilities
└── images/
    └── euno-logo-*.png # Logo variants
```

Modular JavaScript with no build step required.
