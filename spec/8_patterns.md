# Patterns

Rules for pattern discovery, storage, and integration.

Patterns are behavioral regularities discovered through the Recursive Language Model (RLM) during consolidation. They enable anticipation by tracking temporal rhythms, correlations, and goal/interest trajectories.

## Pattern Types

| Type | Purpose | Storage |
|------|---------|---------|
| Temporal | Daily/weekly/seasonal rhythms | `patterns/temporal.json` |
| Correlation | Co-occurrence relationships | `patterns/correlations.json` |
| Trajectory | Goal/concern/interest evolution | `patterns/trajectories.json` |
| Hypothesis | Unvalidated patterns awaiting evidence | `patterns/hypotheses.json` |

## Storage Structure

Patterns are stored per-agent at:
- `data/agents/{id}/patterns/temporal.json`
- `data/agents/{id}/patterns/correlations.json`
- `data/agents/{id}/patterns/trajectories.json`
- `data/agents/{id}/patterns/hypotheses.json`
- `data/agents/{id}/patterns/snapshot_{yyyy}.json` — Historical snapshots

Each file contains:
```json
{
  "version": 1,
  "last_updated": "2025-01-15T14:30:00",
  "patterns": [...]
}
```

Historical snapshots are created at year boundaries (first week of January) to track pattern evolution over time. They mirror identity snapshots and contain temporal, correlations, and trajectories (excluding transient hypotheses).

## Discovery Pipeline

Patterns are discovered during consolidation phase:
1. Load existing patterns from `data/agents/{id}/patterns/`
2. Run multi-pass RLM discovery (temporal → correlation → trajectory)
3. Merge with existing patterns (update confidence if similar found)
4. Apply confidence decay to patterns that weren't re-observed
5. Graduate hypotheses with sufficient evidence
6. Clean up expired hypotheses
7. Create historical snapshot if at year boundary
8. Save updated patterns

Patterns below 0.1 confidence are automatically removed during decay.

## Confidence Model

- New patterns start at 0.5 (neutral)
- Validated: +0.15 per observation
- Not observed: -0.1 decay per consolidation
- Range: 0.0 to 1.0
- High confidence threshold: 0.7

## Hypothesis Graduation

1. Pattern discovered with evidence < threshold → Create Hypothesis
2. Hypothesis expires after 30 days if not validated
3. Evidence >= threshold → Graduate to Pattern
4. Configuration: `metacognition.patterns.min_evidence_for_pattern`

## Schema

### Temporal Pattern
```json
{
  "id": "tmp-abc12345",
  "description": "Morning journaling habit between 6-7 AM",
  "granularity": "daily",  // daily, weekly, seasonal
  "time_window": {"start": "06:00", "end": "07:00"},
  "confidence": 0.85,
  "evidence_count": 12,
  "first_observed": "2025-01-01",
  "last_observed": "2025-01-15"
}
```

### Correlation
```json
{
  "id": "cor-abc12345",
  "type": "co_occurrence",  // co_occurrence, causal, inverse
  "items": [
    {"type": "concern", "pattern": "work stress"},
    {"type": "behavior", "pattern": "evening exercise"}
  ],
  "lag_days": 0,
  "confidence": 0.72,
  "evidence_count": 8,
  "description": "Exercise increases on high-stress days",
  "first_observed": "2025-01-01",
  "last_observed": "2025-01-15"
}
```

### Trajectory
```json
{
  "id": "trj-abc12345",
  "type": "goal_evolution",  // goal_evolution, concern_evolution, interest_shift
  "subject": "Learning Python",
  "stages": [
    {"date": "2025-01-01", "state": "Basic syntax"},
    {"date": "2025-01-10", "state": "Building web apps"}
  ],
  "direction": "expanding",  // clarifying, expanding, resolving, intensifying, diminishing
  "confidence": 0.68,
  "first_observed": "2025-01-01",
  "last_observed": "2025-01-15"
}
```

### Hypothesis
```json
{
  "id": "hyp-abc12345",
  "created_at": "2025-01-15T14:30:00",
  "type": "temporal",
  "hypothesis": "User tends to plan weekly goals on Sunday evenings",
  "evidence_required": 3,
  "evidence_collected": 1,
  "evidence_details": [
    {"date": "2025-01-14", "evidence": "Created weekly planning job at 7 PM Sunday"}
  ],
  "status": "pending",  // pending, validated, rejected, expired
  "expires_at": "2025-02-15"
}
```

## Integration Points

| Context | Patterns Used | How |
|---------|--------------|-----|
| Chat system prompt | User patterns (confidence > 0.7) | Auto-injected for anticipation |
| Consolidation prompt | All patterns for identity updates | Informs identity evolution |
| REST API | Pattern data for external access | `/api/agents/{id}/patterns` |
| Agent tools | Query patterns during conversation | `list_patterns`, `get_pattern_context` |

## Tools

Agents can use these tools to access patterns:
- `list_patterns(agent_id, pattern_type, min_confidence)` - Query patterns
- `get_pattern_context(agent_id, min_confidence)` - Formatted summary for prompts
- `validate_pattern_hypothesis(hypothesis_id, evidence, agent_id)` - Record evidence

## API Endpoints

```
GET  /api/agents/{id}/patterns           - All patterns for agent
GET  /api/agents/{id}/patterns/temporal  - Temporal patterns only
GET  /api/agents/{id}/patterns/correlations
GET  /api/agents/{id}/patterns/trajectories
GET  /api/agents/{id}/patterns/hypotheses
POST /api/agents/{id}/patterns/hypotheses/{hyp_id}/validate - Add evidence
DELETE /api/agents/{id}/patterns/{pattern_id} - Remove pattern
GET  /api/agents/{id}/patterns/context   - Formatted prompt context
GET  /api/agents/{id}/patterns/high-confidence - High confidence only
```

## Configuration

In `data/system/config.json`:
```json
{
  "metacognition": {
    "patterns": {
      "enabled": true,
      "discovery_passes": ["temporal", "correlation", "trajectory"],
      "min_evidence_for_pattern": 3,
      "hypothesis_expiry_days": 30,
      "confidence_decay_rate": 0.1,
      "confidence_boost_on_validation": 0.15
    }
  }
}
```

## Dev CLI

```bash
python main.py dev patterns user          # View all patterns
python main.py dev patterns user --temporal   # Temporal only
python main.py dev patterns user --corr       # Correlations only
python main.py dev patterns user --traj       # Trajectories only
python main.py dev patterns user --hyp        # Pending hypotheses
python main.py dev patterns user --clear      # Reset all patterns
```

## Design Principles

1. **Gradual accumulation**: Patterns strengthen over time with repeated observation
2. **Confidence-gated**: Only high-confidence patterns inform behavior
3. **Hypothesis-driven**: Low-evidence patterns become hypotheses first
4. **Decay without validation**: Patterns weaken if not re-observed
5. **Non-blocking**: Pattern loading failures don't break agent operation
