# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Me and Us (Meandus) is an AI personal assistant that manages user attention to maximize life enjoyment through learning, growth, and contribution. The agent builds an understanding of the user and their world to surface personalized activities and recommendations.

## Current State

This project is in product vision/specification phase. No code yet. Key files:
- `README.md` - Product specification
- `design.md` - Technical architecture and implementation spec
- `todo.md` - Discussion topics to flesh out across sessions

## Development Philosophy

Build for yourself first, not "other people." This is not a solution looking for a problem.

- Build the best agent for the creator's own daily use
- Refine through lived experience, not hypothetical users
- Features get prioritized by real need, rough edges smoothed by real annoyance
- Show to friends and family, gather organic feedback
- Wait for both personal pride AND external signal of demand
- Release only when it's battle-tested and genuinely wanted

The agent is its own first user study. Conjectures about what works get tested against reality.

## Philosophy

The system is grounded in Popperian epistemology: all knowledge is conjecture. Values are not absolute truths but useful generalizations about what promotes life (motion, growth, pleasure, joy, peace, awe). Values are testable and can be refined or discarded.

## Core Architecture (Planned)

1. **Data Ingestion** - Connectors for personal sources (phone, social, financial, calendar) and world sources (events, opportunities)
2. **Log** - One unified stream of all life data, stored as daily flat files with yearly manifests and summaries
3. **Values Engine** - Derives values at three temporal scopes: current (rolling year), life phase (detected), lifetime
4. **World Exploration** - Proactively discovers opportunities matching user values
5. **Attention System** - Three modes: morning briefing, ad-hoc, evening journal
6. **Persuasion** - Advocates for life-promoting activities, overcoming energy conservation bias
7. **Multi-Agent** - Negotiates with other users' agents for social interactions

## Data Storage Structure

```
data/log/
  [yyyy]/
    [yyyy-mm-dd].txt   # daily log entries
    _manifest.txt      # tracks completeness, sources, processing state
    _summary.txt       # comprehensive yearly distillation
```

## When Continuing Spec Work

- Read `todo.md` for pending discussion topics
- Sections marked `[TO BE DEFINED]` in README.md need fleshing out
- Maintain the existing format style (H2 headers, bullet points, concise language)
- Update both README.md and todo.md as topics are completed
