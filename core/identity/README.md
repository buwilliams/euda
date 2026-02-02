# identity

Manage agent identities and consolidation guides.

## Data layout
- Guides: `data/guide/guide-{version}.md` (+ `.json` metadata)
- Identities: `data/identity/{name}/identity-{version}.md` (+ `.json` metadata)
- Prompts: `data/consolidate-system-prompt.md`, `data/consolidate-prompt.md`

## Commands
- `identity guide read|write`
- `identity id create|read|list|write|update`
- `identity consolidate`

## Notes
- Versions auto-increment and are append-only.
- Latest versions are determined by filename version.
- Consolidate uses the latest guide and latest identity.
- Consolidate requires data via stdin, `--text`, or `--file`.
- Identities are kept within size/retention limits from `config.default.json`.
