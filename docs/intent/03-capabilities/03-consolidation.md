# Consolidation (Self-Improvement)

## Key Ideas

- **Euda Learns You**: consolidation is the engine that mines a person's data to understand them. The more data Euda has, the better it knows the person—constantly, in the background.
- **Memory Becomes Identity**: consolidation reads memory and conversation, detects recurring patterns, and writes them into identity. It is how identity is *discovered* rather than configured.
- **Two Phases**: a lightweight *append* after each conversation, and a heavy *consolidate* on a schedule. One keeps memory current; the other does the deep analysis.
- **Small, Earned Diffs**: identity changes incrementally and only when evidence accumulates. Consolidation holds conclusions lightly and preserves history.
- **Growth Is Mutual**: consolidation runs for the user agent and for AI agents alike. Both evolve through the same process.

## Purpose

Consolidation exists so Euda can keep up with a person. People change—their concerns, interests, and even their values shift—and a personal intelligence that does not revise its model of them will slowly become wrong. Consolidation is the always-running process that turns lived data into an updated understanding.

It is the mechanism behind the "consolidate" concern: an agent whose job is to learn the person, mining memory and conversation to surface patterns and feed them into identity. This is what makes the rest of the system improve over time—better curation, better anticipation, better fidelity—simply because Euda keeps learning.

## The Two Phases

### Append (Lightweight, Automatic)

After each conversation, consolidation does a quick extraction of noteworthy items and adds them to short-term memory. It is invisible, non-blocking, and cheap—its job is to make sure nothing worth remembering is lost between the heavier runs. Items an AI agent learns about the user can cross-pollinate into the user agent's memory here.

### Consolidate (Heavy, Triggered)

On a schedule, the consolidate phase does the deep work: it reviews the long-term archive, validates which patterns truly recur, graduates aging short-term memories into the archive, and updates identity with new patterns, interests, and biographical detail. Because it is heavier and meaningful, it is run as a visible topic so the person can see that growth happened.

## Expected Role

Consolidation should be the bridge from memory to identity:

- read memory and conversation as evidence;
- detect what recurs and varies by context, distinguishing what a person says from what they reveal;
- write identity in small diffs, with stated confidence, preserving prior versions;
- decide what stays in focus and what graduates to the archive.

Current implementation details that matter to intent:

- `v1` runs consolidation as a metacognition capability (`agent/cognition/metacognition/consolidation/`), triggered per agent via `config.json`, with append and consolidate phases and logs under `data/system/logs/consolidation/`.
- On `main`, consolidation is a first-class CLI operation: `euda core identity consolidate <name>` takes current identity plus new data and produces a new identity version. A versioned **guide** instructs the process on how to extract patterns and weight sources, and each version records its change ratio against a cap so evolution stays bounded and auditable.
- The guide is explicit that consolidation should *detect patterns, not explain them*: look for what recurs, note what varies by context, update when evidence accumulates, and hold conclusions until earned.

Consolidation should never overwrite a person wholesale or invent patterns from thin evidence. Its discipline—small diffs, earned confidence, preserved history—is what keeps identity honest.

## Future Direction

As models improve, consolidation should detect subtler and longer-range patterns, reason about contested or changing values, and explain *why* it made each identity change with reference to evidence. It should remain bounded, auditable, and reversible no matter how capable it becomes.

The intent to preserve: Euda continually learns the person from their own data, turns that into an honest and evolving identity, and does so transparently—growth a person can inspect, trust, and correct.
