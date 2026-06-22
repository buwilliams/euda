# Web

## Key Ideas

- **Packaging, Not The Product**: the web surface delivers Focus and chat to a browser. It is how people reach Euda today, not what Euda is.
- **One App Among Equals**: on `main`, the web is a single capability (`core/web`), no longer the center of the system.
- **Static App, Local Capability**: the UI stays lightweight and calls into shared capability rather than holding product logic itself.
- **Accessible By Default**: the web exists so a person who does not want to live in a terminal can still use Euda fully.

## Purpose

The web surface exists to make Euda accessible to people. Most people will not operate a personal intelligence from a command line, so the browser is the approachable rendering of Focus and chat—the place where managed attention becomes something a person can simply open and use.

Its role is deliberately bounded. In `v1`, the web application was the whole system; the `main` rewrite reduced it to one capability so that product meaning lives in shared capabilities, not in the UI. This protects the platform idea: the browser is one surface, and the system must not depend on it.

## Expected Role

The web surface should be a thin, accessible delivery of Focus:

- render Focus, chat, and agent management for people in a browser;
- call shared capabilities rather than reimplementing identity, memory, topics, or workflow;
- stay lightweight—mobile-first and buildless in `v1`—so it is easy to deploy and own;
- present the same semantics as every other surface.

Current implementation details that matter to intent:

- `v1` serves the UI from a FastAPI server (Focus, chat, agents) with real-time updates, all backed by `src/core/`.
- On `main`, the web is `core/web`, structured exactly like the other CLI apps, so the browser experience is one capability the router can run alongside the rest.

The web should not become the place where product rules live. It is a surface; the capabilities are shared.

## Future Direction

The web will remain valuable for oversight and approachability even as ambient surfaces grow. As AI improves, the browser may become more supervisory—a place to review what agents did and intervene—rather than a place to drive every step.

The intent to preserve: the web makes Euda accessible without becoming Euda. The product is the personal intelligence beneath it, reachable through many surfaces.
