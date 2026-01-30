# Renderers Specification

Renderers are pluggable UI components that transform structured data into rich visual output in the chat interface. They follow the same external, hot-loadable pattern as skills.

## Architecture

### Narrow Waist Design

Renderers use a **render envelope** format as the stable interface between skills (data producers) and renderers (data consumers):

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Skill     │────▶│  Render Envelope │────▶│   Renderer   │
│ (CLI tool)  │     │    (JSON)        │     │ (JS module)  │
└─────────────┘     └──────────────────┘     └──────────────┘
```

This separation allows:
- Skills to output structured data without knowing how it will be displayed
- Renderers to be added, modified, or replaced without changing skills
- The LLM to pass data through without understanding the visual representation

### Directory Structure

Renderers live in `renderers/` at the project root (outside `src/`):

```
renderers/
├── link-preview/
│   ├── manifest.json    # Metadata and schema
│   └── component.js     # ES module with render()
├── skill-tree/
│   ├── manifest.json
│   └── component.js
└── map-embed/
    ├── manifest.json
    └── component.js
```

## Render Envelope Format

Skills output a JSON envelope wrapped in a code block:

````
```render
{"renderer": "link-preview", "data": {"url": "...", "title": "..."}, "display": "embed"}
```
````

### Envelope Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `renderer` | string | Yes | Name of the renderer to use |
| `data` | object | Yes | Renderer-specific payload |
| `display` | string | No | Display hint: `embed` (default), `modal`, `panel` |

### Code Block Wrapper

The ```` ```render ```` code block wrapper is required because:
1. LLMs preserve code blocks verbatim (they don't summarize or reformat them)
2. The frontend can reliably detect and extract the envelope
3. It's visually distinct in raw output for debugging

## Creating a Renderer

### 1. manifest.json

```json
{
  "name": "link-preview",
  "description": "Display rich link previews from Open Graph metadata",
  "version": "1.0.0",
  "display": ["embed"],
  "schema": {
    "type": "object",
    "properties": {
      "url": { "type": "string", "description": "The URL being previewed" },
      "title": { "type": "string", "description": "Page title" },
      "description": { "type": "string", "description": "Page description" },
      "image": { "type": "string", "description": "Preview image URL" },
      "site_name": { "type": "string", "description": "Site name" }
    },
    "required": ["url"]
  }
}
```

### 2. component.js

ES module that exports a `render()` function:

```javascript
/**
 * Render link preview into container.
 * @param {HTMLElement} container - DOM element to render into
 * @param {Object} data - Data from envelope
 * @param {Object} context - Display context { display: 'embed'|'modal'|'panel' }
 */
export function render(container, data, context) {
    const { url, title, description, image } = data;

    container.innerHTML = `
        <div class="link-preview">
            <h3>${escapeHtml(title || url)}</h3>
            ${description ? `<p>${escapeHtml(description)}</p>` : ''}
        </div>
    `;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

### Styling Guidelines

- Use inline styles or scoped CSS (avoid global styles that leak)
- Use `!important` sparingly but when needed to override parent styles
- Use explicit colors rather than CSS variables (renderers are self-contained)
- Set fixed dimensions on containers to prevent layout shifts

## Skill Integration

Skills that output render envelopes should:

1. **Default to render output** - Make the envelope the default format
2. **Provide text fallback** - Offer `--text` or `--json` flags for plain output
3. **Wrap in code block** - Always wrap the envelope in ```` ```render ````

Example skill command:

```python
@app.command()
def preview(url: str, text: bool = False, json_output: bool = False):
    metadata = fetch_og_metadata(url)

    if json_output:
        print(json.dumps(metadata))
    elif text:
        print(f"Title: {metadata['title']}")
    else:
        # Default: render envelope
        envelope = {"renderer": "link-preview", "data": metadata, "display": "embed"}
        print("```render")
        print(json.dumps(envelope))
        print("```")
```

## LLM Passthrough

The agent system prompt includes instructions to preserve render blocks:

```markdown
## Render Blocks

When a skill outputs a code block with language tag `render` (i.e., ```render),
you MUST include it verbatim in your response without modification. These blocks
contain structured data that the UI will render as rich content. Do not summarize,
describe, or reformat render blocks - pass them through exactly as output by the skill.
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/renderers` | GET | List all available renderers |
| `/api/renderers/{name}` | GET | Get renderer metadata |
| `/api/renderers/{name}/{file}` | GET | Serve renderer files |
| `/api/renderers/refresh` | POST | Force rediscovery of renderers |

## Discovery

Renderers are discovered at startup and cached. The discovery process:

1. Scans `renderers/` for subdirectories
2. Validates each has `manifest.json` and `component.js`
3. Loads and validates manifest against schema
4. Caches results until refresh

Hot-loading is supported via cache-busting query parameters on dynamic imports.

## Built-in Renderers

| Renderer | Description | Data Fields |
|----------|-------------|-------------|
| `link-preview` | Open Graph link previews | url, title, description, image, site_name |

## Future Considerations

- **Renderer authoring by agents**: Euno could potentially create new renderers
- **Renderer marketplace**: Share renderers between Euno instances
- **Display modes**: Support for modal, panel, and other display contexts
- **Renderer dependencies**: Allow renderers to declare JS/CSS dependencies
