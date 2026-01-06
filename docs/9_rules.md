# Rules

*Prioritized assertions for detecting implementation drift. Each rule is one line and verifiable.*

---

## Priority 1: Core Identity

These define what Euno is. Violating these means building the wrong thing.

1. Every LLM API call includes the user profile in the system prompt
2. Agents are generic: config.json + persona.md + tools + loop — no agent-specific Python code
3. Adding a new agent requires only creating a directory with config.json and persona.md
4. Jobs are the only work structure — no separate "tasks" or "projects" tables
5. Jobs are hierarchical via parent_id, unlimited depth
6. The user is conceptually an agent with a different interface (Web UI vs autonomous loop)

---

## Priority 2: Agent Behavior

How agents must operate to maintain the system's integrity.

7. Agents wake only on trigger events — no polling, no sleep loops
8. Agents end work cycles by calling done_working — never by timing out silently
9. max_work_iterations is a safety limit, not normal termination
10. Event scoping: job:assigned only wakes the assigned agent, not all subscribers
11. Agents log all activity to logs/{date}.json with structured events
12. Conversation history is session-based: state/conversation/{session-id}.md

---

## Priority 3: Data Integrity

Where data lives and how it's structured.

13. Jobs stored in SQLite at data/jobs/db.sqlite — not flat files
14. Job assets stored in data/jobs/assets/{job-id}/ — one directory per job
15. User profile is a single markdown file: data/user/user-profile.md
16. Lifelog entries are daily markdown files: data/user/lifelog/{date}.md
17. System config is JSON: data/system/config.json
18. Agent state lives in data/agents/{agent-id}/ — nowhere else

---

## Priority 4: User Experience

How the interface must feel and behave.

19. Value is delivered before any user interaction — open app, see what matters
20. Instant feedback: create job → job exists immediately, no confirmation dialogs
21. Smart defaults: filenames auto-generated from content, timestamps auto-added
22. Chat expands in place — no screen switching to have a conversation
23. Focus tab is the default tab, not Chat
24. The interface adapts to time of day (morning/active/evening views)

---

## Priority 5: Visual Design

Concrete UI implementation requirements.

25. Single-column centered layout, max-width 640px
26. Background: #f8f8f8 (off-white), cards/inputs: #fff (white)
27. Primary buttons use #333 (dark) — blue (#007bff) only for focus states and links
28. All icons are HeroIcons 24px outline variants from /static/icons/
29. All navigation uses slide animations (0.3s) for spatial continuity
30. Font: Roboto with system font fallback

---

## Priority 6: API Contract

How the web layer must behave.

31. REST endpoints follow pattern: GET/POST /api/{resource}, GET/PATCH /api/{resource}/{id}
32. Real-time updates via SSE at /api/events — not WebSocket, not polling
33. Static files served from /static/ — no build step required
34. Chat endpoint accepts agent parameter to talk to specific agents

---

## Priority 7: Security & Operations

Non-negotiable operational requirements.

35. No secrets in code — all credentials via .env file
36. Authentication required for all /api/* endpoints except /api/health
37. Sessions stored server-side, not in JWT tokens
38. Agents cannot modify their own config.json or persona.md

---

## How to Use This Document

When reviewing implementation:

1. Start from Priority 1 and work down
2. For each rule, find the code/data that proves compliance
3. Flag violations with rule number: "Violates Rule 7: polling loop in curator.py"
4. Drift in Priority 1-3 is critical; Priority 4-7 is important but less urgent

When adding features:

1. Check if the feature would violate any rule
2. If yes, either change the approach or propose a rule amendment
3. Rule amendments require explicit discussion — don't just update this file
