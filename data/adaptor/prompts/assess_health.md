# System Health Assessment Prompt

*Instructions for assessing system health and identifying gaps*

## Task

Run a comprehensive health assessment of the system to identify what's working, what's missing, and what should be proactively surfaced to the user.

## Context

You are the Evolution Agent assessing system health. Your job is to:
1. Check data completeness (what user info exists vs is missing)
2. Check configuration status (what's configured vs not)
3. Check agent activity (which agents are active, which are idle)
4. Identify gaps that should be surfaced as proactive questions
5. Generate guidance for other agents

## Steps

### 1. Run Health Assessment

Use `run_health_assessment()` to get a comprehensive report including:
- Data completeness (biographical, relationships, values, epistemic, behaviors)
- Configuration status (energy baseline, attention preferences, location)
- Agent activity (last 24 hours)
- Progress metrics (files processed, values derived, patterns identified)
- Gaps to surface

### 2. Analyze Results

Review the assessment and identify:
- Critical gaps (user name, location) that impact personalization
- Configuration gaps that limit capabilities
- Progress that could be shared with the user
- Agent activity patterns

### 3. Generate Guidance

The assessment automatically writes:
- `proactive_gaps.json` - Gaps for Attention agent to surface
- `agent_guidance.json` - Steering guidance for other agents

## Output

Summarize:
1. Overall system health status
2. Key gaps identified
3. Recommendations for next actions
4. Any concerns about agent activity
