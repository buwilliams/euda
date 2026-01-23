# Tests

Rules for testing. Tests enforce the specs and docs, not the implementation details.

## Test Categories

- **Invariant tests** (`tests/invariants/`) — design invariants derived from specs
- **Unit tests** (`tests/unit/`) — individual component behavior
- **E2E tests** (`tests/e2e/`) — end-to-end UI flows with Playwright

## Invariant Tests

- Test design rules from specs, not implementation details
- Each test file maps to a spec file (e.g., `test_agent_states.py` tests `specs/1_agents.md`)
- Document which spec rules are being tested with comments

## Unit Tests

- Test individual functions and classes in isolation
- Mock external dependencies (LLM calls, file I/O, network)
- Focus on behavior, not implementation

## E2E Tests

- Use Playwright with Python for browser automation
- Run in headless Chromium by default
- Mobile-first viewport (390x844)

### Selectors

- Use `data-testid` attributes for all test selectors
- Never use CSS classes, tag names, or text content for selectors
- Never use `get_by_text()` — it's ambiguous and breaks when text appears multiple times

### data-testid Conventions

- **Tabs:** `tab-{name}`, `tab-btn-{name}`
- **Buttons:** `{action}-btn` (e.g., `send-btn`, `pause-btn`, `back-btn`)
- **Inputs:** `{field-name}` (e.g., `context-input`, `budget-limit`)
- **Containers:** `{component}-content` or `{component}-container`
- **Cards:** `{type}-card` (e.g., `job-card`, `agent-card`)
- **Messages:** `message-{role}` (e.g., `message-user`, `message-agent`)
- **Menu items:** `menu-{name}` or `overflow-{name}`
- **Collapsible sections:** `section-{name}` (e.g., `section-timelines`, `section-llms`)

### Test Structure

- Group tests by feature in separate files (e.g., `test_auth.py`, `test_focus.py`)
- Use descriptive class names (e.g., `TestTabSwitching`, `TestBackNavigation`)
- Use fixtures for common setup (e.g., `authenticated_page`, `unauthenticated_page`)
- Skip tests that require external services (LLM responses) by default

### Running Tests

```bash
uv run pytest tests/e2e/ -v              # Headless (default)
uv run pytest tests/e2e/ -v --headed     # With browser visible
uv run pytest tests/e2e/ -v --headed --slowmo=500  # Slow for debugging
```
