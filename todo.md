# Implementation Todo

## Todo

- [ ] Render markdown in chat (bold, italic, lists, headers, code blocks)
- [ ] Integrate proactive surfacing into UI - show real surfaced content in activity area
- [ ] Poll for attention queue items (morning attention, evening prompts, opportunities)
- [ ] "All quiet" only appears when there truly is nothing to surface
- [ ] Morning attention: show today's calendar events
- [ ] Morning/evening notification triggers (email/push)
- [ ] Weekly review: patterns from past week, upcoming prep
- [ ] File upload support in web UI
- [ ] URL fetching: "Read this article and log what's interesting"
- [ ] Photo/image processing via chat
- [ ] Filter logs by source/type
- [ ] Edit public value card via UI
- [ ] REST endpoint for card exchange
- [ ] Email notifications
- [ ] Push notifications (web/mobile)
- [ ] Image OCR/description
- [ ] PDF text extraction
- [ ] Audio transcription
- [ ] Video processing
- [ ] Calendar API (Google/Apple)
- [ ] Theme system (user customizable)
- [ ] Mobile responsive refinements
- [ ] Keyboard shortcuts

## Completed

- [x] Verify end-to-end flow works (inbox → ingestion → logs, chat → intent → response)
- [x] Fix Agent Status endpoint to read real state files
- [x] Fix agent process() to accumulate text from responses with tool calls
- [x] Fix list_pending_files() to show full paths
- [x] Design and build new minimal UI (black text, white background, typography-first)
- [x] Chat as primary interface with activity feed
- [x] Add logo and loading states
