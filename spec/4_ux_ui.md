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
- Agent Manage view uses sub-views: Profile, Config, Memory, Monitoring — each stacks forward with back button
- Action buttons show running state during async operations (spinning icon, disabled siblings)
