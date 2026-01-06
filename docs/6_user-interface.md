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
3. Tagline fades in (400ms)
4. Pronunciation ("you-know") fades in below (300ms)
5. Hold (800ms)
6. Crossfade to login modal or main app

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
│  │  │  │    (Focus / Chat / History / About / Settings)│  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │           tab-menu                            │  │  │  │
│  │  │  │       [☐ Focus 3] [💬 Chat] [••• More]        │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              input-bar                              │  │  │
│  │  │   [What's on your mind?              ] [➤]          │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Layout notes:**
- Single-column centered layout (max 640px)
- Off-white background (#f8f8f8) with white cards/inputs for contrast
- Three main tabs: Focus (default), Chat, More (overflow menu)
- More menu contains: History, About, Settings, New Chat

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

Three main tabs with an overflow menu:

| Tab | Icon | Purpose |
|-----|------|---------|
| Focus | queue-list | Task and project management (Things-like) — **default tab** |
| Chat | chat-bubble-left | Conversation with Euno |
| More | ellipsis-vertical | Overflow menu for less-used screens |

**Overflow Menu (More):**
| Item | Icon | Purpose |
|------|------|---------|
| History | clock | Past conversation browser |
| About | information-circle | About page (docs/1_pitch.md content) |
| Settings | cog-6-tooth | App settings and agent management |
| New Chat | arrow-path | Start a new conversation session |

**Focus badge:** Shows count of tasks due today

**Chat notification:** Send button pulses when a response arrives while on another tab (auto-clears after 3 seconds)

### Input Bar

Bottom-anchored bar with text input and send button.

```
┌─────────────────────────────────────────────┐
│  ┌─────────────────────────────────────┐ ┌──┐ │
│  │ What's on your mind?                │ │➤│ │
│  └─────────────────────────────────────┘ └──┘ │
└─────────────────────────────────────────────┘
```

**Components:**
- **Text input** — Auto-expanding textarea with placeholder "What's on your mind?"
- **Send button** — Paper plane icon, black background (#333); pulses on new response

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

Past conversation browser with session-based storage.

```
┌──────────────────────────────────────┐
│ Today 14:30                          │
│ What should I focus...               │
├──────────────────────────────────────┤
│ Today 09:15                          │
│ Good morning, I wanted to talk...    │
├──────────────────────────────────────┤
│ Yesterday 16:45                      │
│ Can you help me plan...              │
└──────────────────────────────────────┘
```

**Session Storage:**
- Each conversation is stored as `{session-id}.md`
- Session ID format: `YYYY-MM-DD_HHMMSS` (e.g., `2026-01-03_143022`)
- Multiple conversations per day supported
- "New Chat" (in More menu) creates a new session
- Legacy date-only files (`YYYY-MM-DD.md`) supported for backwards compatibility

**List Items:**
- Friendly date (Today/Yesterday/date) and time
- Preview of first user message (truncated to 100 chars)
- Message count
- Click to view details

**Detail View:**
- Full preview and message count
- Continue Conversation — loads messages into chat, continues in same session
- Archive — removes from history (currently same as delete)
- Delete — permanently removes conversation file

**Continue Behavior:**
- Sets session ID to the selected conversation
- Loads all messages into chat UI
- New messages append to the same session file

### Settings Tab

Application settings and agent management.

```
┌──────────────────────────────────────┐
│ Agents                               │
├──────────────────────────────────────┤
│ ✓ Friend                         → │
│ ✓ Worker                         → │
│ ○ Curator                        → │
│ ○ Profiler                       → │
└──────────────────────────────────────┘
```

**Agent List:**
- Shows all configured agents with enabled/disabled status
- Toggle icon: check (enabled) or circle (disabled)
- Click to view/edit agent details

**Agent Detail View:**
- Enable/disable toggle
- View and edit persona (markdown)
- View and edit config (JSON)
- Changes saved immediately to disk

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
- Primary buttons: #333 background, #fff icon/text (dark, not blue)
- Accent blue (#007bff) reserved for focus states and links only

**Button Colors:**
Primary action buttons (Send, Add, Save) use dark backgrounds (`--color-accent-dark: #333`) rather than blue. This provides a more professional, understated appearance. Blue accent color is reserved for:
- Input focus rings
- Links
- Selected/active state indicators

**Spacing:**
- Base unit: 0.5rem (8px)
- Content padding: 1.5rem
- Max content width: 640px

**Transitions:**
- Hover states: 0.15s ease

**Icons:**
All icons use [HeroIcons](https://heroicons.com/) (MIT licensed, by Tailwind Labs):
- Style: 24px outline variants
- Format: SVG with `stroke="currentColor"` for color inheritance
- Location: `/static/icons/`

Icon usage pattern in JavaScript:
```javascript
function icon(name, className = '') {
    const cls = className ? ` class="${className}"` : '';
    return `<img src="/static/icons/${name}.svg" alt="${name}"${cls}>`;
}
```

For white icons on dark buttons, apply `filter: invert(1)` in CSS.

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

Tab order for direction: Focus (0) → Chat (1) → History (2) → About (3) → Settings (4)

Switching from Focus to Chat slides left; Chat to Focus slides right.

---

## State Management

**Client-side state:**
```javascript
sessionId          // Current chat session ID, format: YYYY-MM-DD_HHMMSS (localStorage)
                   // null when starting new conversation (server generates new ID)
viewingHistorySessionId  // Session being viewed from history (for UI state)
activeTab          // 'focus' | 'chat' | 'history' | 'about' | 'settings'
previousTab        // Previous tab for animation direction
focusView          // 'menu' | 'today' | 'upcoming' | 'anytime' | 'someday' | 'completed' | 'job-{id}' | 'completed-{id}' | 'assets-{id}' | 'asset-{id}-{filename}'
focusViewHistory   // Stack for back navigation
historyView        // 'list' | 'conversation-{session-id}'
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

## Swipe & Drag Gestures

Job cards support swipe (mobile) and click-drag (desktop) gestures for quick actions.

**Active Jobs:**
| Gesture | Action |
|---------|--------|
| Swipe/drag left | Complete job |
| Swipe/drag right | Open When picker |

**Completed Jobs:**
| Gesture | Action |
|---------|--------|
| Swipe/drag left | Delete job |
| Swipe/drag right | Restore to active |

**Visual Feedback:**
- Light gray background with icon appears during gesture
- Icon and background change color when threshold is reached:
  - Green tint for Complete/Restore
  - Blue tint for When picker
  - Red tint for Delete
- If gesture doesn't reach threshold, card springs back (action cancelled)
- Desktop: cursor changes to "grab" to indicate draggable

**Where swipe/drag is enabled:**
- Today jobs on Focus landing
- Timeline views (Upcoming, Anytime, Someday)
- Completed jobs list
- Child jobs in job detail views
- Child jobs in agent inbox views
- Child jobs in "Add Jobs" screen

**Implementation notes:**
- Threshold: 80px horizontal movement to trigger action
- Max distance: 120px (clamped)
- Vertical movement cancels horizontal swipe (allows scrolling)
- Click navigation still works if no drag occurred

---

## File Structure

```
static/
├── index.html          # Main HTML shell
├── css/
│   ├── variables.css   # CSS custom properties
│   ├── base.css        # Reset and base styles
│   ├── layout.css      # App structure and tabs
│   ├── components.css  # Reusable components
│   ├── chat.css        # Chat tab styles
│   ├── focus.css       # Focus tab styles
│   ├── swipe.css       # Swipe gesture styles
│   ├── when-picker.css # Date picker modal
│   ├── history.css     # History tab styles
│   ├── about.css       # About tab styles
│   ├── auth.css        # Login/auth styles
│   └── responsive.css  # Mobile adaptations
├── js/
│   ├── init.js         # App initialization and routing
│   ├── state.js        # Global state management
│   ├── splash.js       # Splash screen animation
│   ├── auth.js         # Authentication and login modal
│   ├── tabs.js         # Tab navigation with animations
│   ├── chat.js         # Chat tab functionality
│   ├── focus.js        # Focus tab (tasks/projects)
│   ├── swipe.js        # Swipe/drag gesture handling
│   ├── history.js      # History tab
│   ├── about.js        # About tab
│   ├── upload.js       # File upload handling
│   └── utils.js        # Shared utilities
├── icons/              # HeroIcons SVG files
│   ├── sun.svg, calendar.svg, clock.svg, cloud.svg
│   ├── check.svg, plus.svg, trash.svg, pencil.svg
│   ├── folder.svg, document.svg, link.svg
│   ├── bolt.svg, user.svg, chevron-left.svg
│   ├── chat-bubble-left.svg, queue-list.svg
│   ├── ellipsis-vertical.svg, cog-6-tooth.svg
│   ├── arrow-path.svg, arrow-up-tray.svg
│   └── ... (all from heroicons.com)
└── images/
    └── favicon.svg     # App favicon
```

Modular CSS and JavaScript with no build step required.
