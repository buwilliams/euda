# Memory

## Key Ideas

- **Memory Enables Anticipation**: Euda tracks what is on an agent's mind so it can act before being asked. Memory is what turns a tool into an intelligence.
- **Two Horizons**: short-term memory holds current concerns; long-term memory is a permanent archive of lived experience.
- **Memory, Not Meaning**: the long-term archive preserves what happened with high fidelity. Meaning is derived from it later, during consolidation—it is not baked in at write time.
- **Graduation, Not Deletion**: short-term entries do not vanish when they age; they graduate into the long-term archive.
- **Every Agent Remembers**: the user agent and every AI agent have the same memory model. The more a person shares, the better Euda knows them.

## Purpose

Memory exists so agents can anticipate. Without it, every interaction starts cold and the system can only react. With it, an agent can notice that a concern from last week is now due, that a pattern is forming across months, that something a person mentioned in passing matters now.

Memory is also the raw material of identity. Consolidation reads memory to discover the patterns that become an agent's identity. A rich, honest archive is what lets Euda's model of a person deepen over time.

## The Two Horizons

### Short-Term Memory

A rolling window (90 days in `v1`) of the items currently worth an agent's attention. Entries are small and typed—`person`, `place`, `thing`, `goal`, `concern`, `idea`, `learning`, `behavior`—each with what it is, when it was mentioned, and when it is expected to matter. Short-term memory is what an agent scans to decide what would most help today.

### Long-Term Memory

A permanent, chronological archive of lived experience, written as dated entries and kept year by year. It is high-fidelity and append-only: the goal is to preserve the record, not to summarize it away. Semantic access and pattern analysis happen on top of the archive when needed, rather than forcing every memory into a fixed shape at the moment it is stored.

## Expected Role

Memory should be the durable substrate beneath anticipation and identity:

- Agents write to short-term memory continuously as they observe and work.
- Items age out of short-term memory and **graduate** to the long-term archive rather than being lost.
- Consolidation reads memory to update identity and to decide what is worth keeping in focus.
- Memory flows between agents where it serves the person: items an AI agent learns about the user can cross-pollinate into the user agent's memory, so the person's model is enriched no matter which agent did the observing.

Current implementation details that matter to intent:

- `v1` stores short-term memory as `short-term.jsonl` and long-term memory as dated markdown under `long-term/{year}/`, per agent.
- On `main`, memory is its own CLI app (`euda core memory`) with `write`, `read`, `search`, `prune`, and `clear`, keeping the same short-term / long-term archive shape per agent.
- Memory is kept human-readable so a person can inspect, correct, and own what the system remembers about them.

## Future Direction

As agents improve, memory should support richer recall and pattern detection across longer spans without losing its plain, inspectable form. The archive may grow to support better semantic retrieval, cross-agent context sharing, and provenance for how a memory informed an identity change.

The intent to preserve: memory should always remain *the person's*—readable, correctable, and high-fidelity—so that the better Euda's recall becomes, the more it serves the person rather than surveils them.
