# Test Coverage Map

Mapping design requirements from `docs/3_system.md` and `specs/*.md` to test coverage.

## Legend
- [x] Tested
- [ ] Not tested
- [~] Partially tested

---

## docs/3_system.md - Ontology

### Identity
| Requirement | Tested | Notes |
|-------------|--------|-------|
| Identity stored in identity.md | [ ] | No tests for identity loading |
| Identity evolves through consolidation | [ ] | Consolidation modules 0% coverage |

### Cognition
| Requirement | Tested | Notes |
|-------------|--------|-------|
| Token awareness for budget enforcement | [x] | test_token_budget.py |
| Progress awareness for stuck detection | [ ] | progress.py 30% coverage |
| Consolidation for memory processing | [ ] | consolidation modules 0-35% |

### Memory
| Requirement | Tested | Notes |
|-------------|--------|-------|
| Short-term memory 90-day rolling | [x] | test_memory_expiration.py |
| Long-term memory permanent archive | [~] | Basic write/read tested |
| Memory types validated | [x] | test_memory_expiration.py |

### Behavior
| Requirement | Tested | Notes |
|-------------|--------|-------|
| Tools limited to agent config | [x] | test_tool_access.py |
| Triggers create topics | [ ] | manager.py 0% coverage |

---

## docs/3_system.md - Lifecycle

### Topics
| Requirement | Tested | Notes |
|-------------|--------|-------|
| Topics with waiting:* not actionable | [x] | test_topic_actionability.py |
| Topics with blocked:* not actionable | [x] | test_topic_actionability.py |
| Topics with someday=true not actionable | [x] | test_topic_actionability.py |
| Topics with future due_date not actionable | [x] | test_topic_actionability.py |
| Topic handoff with pending_from | [x] | test_topics.py |
| Unblock removes blocking tags | [x] | test_topic_actionability.py |

### Manager
| Requirement | Tested | Notes |
|-------------|--------|-------|
| Loads agent configs from data/agents/ | [ ] | manager.py 0% coverage |
| Starts each agent in own thread | [ ] | manager.py 0% coverage |
| Creates trigger topics at scheduled times | [ ] | manager.py 0% coverage |
| Detects missed triggers at startup | [ ] | manager.py 0% coverage |

### Agent States
| Requirement | Tested | Notes |
|-------------|--------|-------|
| Three states: enabled, disabled, paused | [x] | test_agent_states.py |
| enabled → paused on threshold breach | [x] | test_agent_states.py |
| paused → enabled requires manual | [x] | test_agent_states.py |
| State persists to config.json | [x] | test_agent_states.py |

### Work Cycle
| Requirement | Tested | Notes |
|-------------|--------|-------|
| One topic per work cycle | [x] | test_work_cycle.py |
| Agent calls done_working to complete | [ ] | No tests for done_working |
| Max iterations configurable | [ ] | agent.py 23% coverage |

---

## specs/1_agents.md

### Token Awareness
| Requirement | Tested | Notes |
|-------------|--------|-------|
| Pre-call estimation | [~] | acquire() tested |
| Post-call recording | [x] | record() tested |
| Per-agent budgets split equally | [x] | test_token_budget.py |
| Auto-pause at threshold | [x] | test_token_budget.py |
| Frequency-based limits (daily/hourly/etc) | [x] | test_token_budget.py |

### Progress Awareness
| Requirement | Tested | Notes |
|-------------|--------|-------|
| Counts tool calls per iteration | [ ] | progress.py 30% |
| Detects stuck patterns | [ ] | progress.py 30% |
| Breaks work cycle when stuck | [ ] | agent.py 23% |

### Consolidation
| Requirement | Tested | Notes |
|-------------|--------|-------|
| Append phase after conversations | [ ] | append.py 0% |
| Consolidate phase on trigger | [ ] | consolidate.py 0% |

---

## specs/2_data.md

### Short-term Memory
| Requirement | Tested | Notes |
|-------------|--------|-------|
| 90-day expiration | [x] | test_memory_expiration.py |
| Valid types enforced | [x] | test_memory_expiration.py |
| Expired entries archive to long-term | [x] | test_memory_expiration.py |

### Long-term Memory
| Requirement | Tested | Notes |
|-------------|--------|-------|
| Year-based directory structure | [x] | test_memory.py |
| Entries append to daily file | [x] | test_memory.py |

### Patterns
| Requirement | Tested | Notes |
|-------------|--------|-------|
| Confidence >= 0.7 for prompts | [x] | test_pattern_confidence.py |
| Confidence decays without validation | [x] | test_pattern_confidence.py |
| Confidence boosts on validation | [x] | test_pattern_confidence.py |

### Topic Assets
| Requirement | Tested | Notes |
|-------------|--------|-------|
| Assets stored as files | [ ] | assets.py 34% coverage |
| List/read/write assets | [ ] | No asset tests |

---

## Untested Modules (0% coverage)

These modules have no test coverage and may contain obsolete code:

| Module | Purpose | Priority |
|--------|---------|----------|
| src/agent/manager.py | Agent orchestration | HIGH |
| src/agent/cognition/metacognition/consolidation/append.py | Memory extraction | HIGH |
| src/agent/cognition/metacognition/consolidation/consolidate.py | Identity evolution | HIGH |
| src/cli/* | CLI commands | LOW |
| src/llms/chatgpt.py | ChatGPT client | MEDIUM |
| src/llms/grok.py | Grok client | MEDIUM |
| src/web/* | Web routes | LOW |

---

## Priority Tests Needed

1. **Progress Awareness** - Stuck detection is mentioned in design but only 30% covered
2. **Consolidation Flow** - Core to design ("identity evolves through consolidation") but 0% covered
3. **Manager Triggers** - "Triggers create topics" is core behavior but 0% coverage
4. **done_working Tool** - How agents signal completion, not tested
