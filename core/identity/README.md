# identity

Manage agent identities and cognitive schemas.

## Data layout
- Schemas: `data/schema/{schema}-{version}.json`
- Identities: `data/identity/{schema}/{name}-{version}.json`
- Prompts: `data/consolidate-system-prompt.md`, `data/consolidate-prompt.md`

## Commands
- `identity schema create/get/latest/list`
- `identity identity create/get/latest/list`
- `identity identity tail-working [--run-id <id>]`
- `identity consolidate`
- `identity update`

## Notes
- Identities are versioned; `consolidate` writes a new version.
- `update` modifies the latest identity in-place for incremental updates.
- Consolidation uses memory/topics/stdin/inline inputs and LLM prompts.
- Memory entries are summarized before consolidation and batched by `--max-chars` to fit context windows.
- Default caps: `--max-chars 200000`, `--summary-max-chars 20000`.
- Use `--summary-max-chars` to cap summary chunk size and `--llm-timeout` to increase per-call timeouts.
