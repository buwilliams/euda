"""
RLM Client

Manages RLM sessions for memory access.
Based on the Recursive Language Models paper (arXiv:2512.24601v1).
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Callable

from .repl import REPLEnvironment, ExecutionResult
from ..llms.base import get_client, UnifiedClient


@dataclass
class RLMResult:
    """Result of an RLM session."""
    query: str
    findings: str  # Synthesized answer
    sources: list[dict] = field(default_factory=list)  # Referenced memory entries
    iterations: int = 0
    sub_calls: int = 0
    error: Optional[str] = None


@dataclass
class RLMConfig:
    """Configuration for RLM sessions."""
    max_iterations: int = 20
    max_recursion_depth: int = 1
    execution_timeout_seconds: int = 30
    output_truncation_chars: int = 10000


def _load_rlm_config() -> RLMConfig:
    """Load RLM configuration from system config."""
    import json
    from pathlib import Path

    config_path = Path(__file__).parent.parent.parent / "data" / "system" / "config.json"
    if not config_path.exists():
        return RLMConfig()

    try:
        with open(config_path) as f:
            config = json.load(f)
        rlm_config = config.get("rlm", {})
        return RLMConfig(
            max_iterations=rlm_config.get("max_iterations", 20),
            max_recursion_depth=rlm_config.get("max_recursion_depth", 1),
            execution_timeout_seconds=rlm_config.get("execution_timeout_seconds", 30),
            output_truncation_chars=rlm_config.get("output_truncation_chars", 10000)
        )
    except (json.JSONDecodeError, KeyError):
        return RLMConfig()


class RLMClient:
    """Manages RLM sessions for memory access.

    This client mediates all long-term memory access through a REPL environment
    where the LLM can write code to search, filter, and analyze memory entries.
    """

    def __init__(self, llm_client: UnifiedClient = None, agent_id: str = "user"):
        """
        Initialize the RLM client.

        Args:
            llm_client: LLM client for making calls (uses default if not provided)
            agent_id: ID of the agent using this client
        """
        self.client = llm_client or get_client()
        self.agent_id = agent_id
        self.config = _load_rlm_config()

        # Track session state
        self._sub_call_count = 0
        self._iteration_count = 0

    def _create_llm_query_fn(self, depth: int = 0) -> Callable[[str], str]:
        """Create the llm_query function for the REPL.

        Args:
            depth: Current recursion depth

        Returns:
            Function that makes sub-LLM calls
        """
        def llm_query(prompt: str) -> str:
            """Query the LLM for semantic analysis."""
            if depth >= self.config.max_recursion_depth:
                return "[Error: Maximum recursion depth reached]"

            self._sub_call_count += 1

            try:
                response = self.client.create(
                    max_tokens=2000,
                    system="You are a helpful assistant analyzing memory content. "
                           "Provide concise, factual analysis. Be direct and brief.",
                    messages=[{"role": "user", "content": prompt}],
                    agent_id=f"rlm-{self.agent_id}",
                    track_cost=True
                )

                # Extract text from response
                for block in response.content:
                    if hasattr(block, 'text'):
                        return block.text

                return "[No response from LLM]"

            except Exception as e:
                return f"[Error in llm_query: {str(e)}]"

        return llm_query

    def _extract_code_blocks(self, text: str) -> list[str]:
        """Extract Python code blocks from LLM response."""
        # Match ```python ... ``` or ``` ... ```
        pattern = r'```(?:python)?\s*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        return matches if matches else []

    def _truncate_output(self, output: str) -> str:
        """Truncate output to configured limit."""
        if len(output) > self.config.output_truncation_chars:
            return output[:self.config.output_truncation_chars] + "\n[Output truncated...]"
        return output

    def _build_system_prompt(self, task_type: str) -> str:
        """Build the system prompt for RLM sessions."""
        return f"""You are accessing an agent's long-term memory through a REPL environment.

## Available Variables
- `memory['entries']`: List of all memory entries with date, content, source
- `memory['by_date']`: Dict mapping dates to full markdown content
- `memory['metadata']`: Info about the memory store (total_chars, date_range, total_entries)

## Available Functions
- `llm_query(prompt)`: Ask a sub-LLM to analyze text semantically. Use this to understand content.
- `print()`: Output information to continue reasoning
- `FINAL(answer)`: Declare your final answer (string)
- `FINAL_VAR(var_name)`: Declare a variable as the final answer

## Available Modules
- `re`: Regular expressions
- `json`: JSON parsing
- `datetime`: Date/time utilities
- `collections`: Counter, defaultdict, etc.
- `itertools`: Iteration tools
- `math`: Math functions

## Your Task
{task_type}

## Strategy
1. First examine memory structure: `print(memory['metadata'])`
2. Search for relevant content using code (string matching, date filtering)
3. Use `llm_query()` to semantically analyze promising chunks
4. Synthesize findings into a clear answer
5. Call `FINAL(your_answer)` when done

## Example Session
```python
# First, understand what we have
print(memory['metadata'])

# Find entries mentioning goals
goal_entries = [e for e in memory['entries'] if 'goal' in e['content'].lower()]
print(f"Found {{len(goal_entries)}} entries mentioning goals")

# Analyze the most recent ones
for entry in goal_entries[-5:]:
    analysis = llm_query(f"What goals are mentioned here? {{entry['content'][:1000]}}")
    print(f"{{entry['date']}}: {{analysis}}")

# Synthesize findings
FINAL("The main goals mentioned are: 1) ..., 2) ..., 3) ...")
```

Write Python code to explore the memory and answer the query.
After each code block, I will show you the output so you can continue reasoning.
When you have enough information, use FINAL() to provide your answer."""

    def _run_session(self, query: str, memory: dict, task_type: str) -> RLMResult:
        """Run an RLM session.

        Args:
            query: The user's query
            memory: Memory data structure
            task_type: Description of the task for the system prompt

        Returns:
            RLMResult with findings
        """
        self._sub_call_count = 0
        self._iteration_count = 0

        # Create REPL environment
        llm_query_fn = self._create_llm_query_fn(depth=0)
        repl = REPLEnvironment(memory, llm_query_fn)

        # Build conversation
        system_prompt = self._build_system_prompt(task_type)
        messages = [{"role": "user", "content": f"Query: {query}"}]

        # Track sources for attribution
        sources = []

        # Iteration loop
        while self._iteration_count < self.config.max_iterations:
            self._iteration_count += 1

            # Get LLM response
            try:
                response = self.client.create(
                    max_tokens=4000,
                    system=system_prompt,
                    messages=messages,
                    agent_id=f"rlm-{self.agent_id}",
                    track_cost=True
                )
            except Exception as e:
                return RLMResult(
                    query=query,
                    findings="",
                    error=f"LLM call failed: {str(e)}",
                    iterations=self._iteration_count,
                    sub_calls=self._sub_call_count
                )

            # Extract assistant response text
            assistant_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    assistant_text += block.text

            messages.append({"role": "assistant", "content": assistant_text})

            # Extract and execute code blocks
            code_blocks = self._extract_code_blocks(assistant_text)

            if not code_blocks:
                # No code found - check if there's a final answer in text
                if "FINAL" in assistant_text:
                    # Try to extract answer from text
                    match = re.search(r'FINAL\(["\'](.+?)["\']\)', assistant_text)
                    if match:
                        return RLMResult(
                            query=query,
                            findings=match.group(1),
                            sources=sources,
                            iterations=self._iteration_count,
                            sub_calls=self._sub_call_count
                        )

                # Ask for code
                messages.append({
                    "role": "user",
                    "content": "Please write Python code to explore the memory. "
                              "Wrap your code in ```python ... ``` blocks."
                })
                continue

            # Execute each code block
            all_output = []
            final_result = None

            for code in code_blocks:
                result = repl.execute(
                    code,
                    timeout=self.config.execution_timeout_seconds
                )

                if result.output:
                    all_output.append(result.output)

                if result.error:
                    all_output.append(f"[Error]: {result.error}")

                if result.final_answer:
                    final_result = result
                    break

            # Combine output
            combined_output = self._truncate_output('\n'.join(all_output))

            # Check for final answer
            if final_result and final_result.final_answer:
                return RLMResult(
                    query=query,
                    findings=final_result.final_answer,
                    sources=sources,
                    iterations=self._iteration_count,
                    sub_calls=self._sub_call_count
                )

            # Continue conversation with output
            messages.append({
                "role": "user",
                "content": f"Output:\n```\n{combined_output}\n```\n\n"
                          "Continue exploring or call FINAL() with your answer."
            })

        # Max iterations reached
        return RLMResult(
            query=query,
            findings="Maximum iterations reached without finding an answer.",
            sources=sources,
            iterations=self._iteration_count,
            sub_calls=self._sub_call_count,
            error="Max iterations reached"
        )

    def recall(self, query: str, memory: dict, time_range_days: int = 365) -> RLMResult:
        """
        RLM-powered memory recall.

        Args:
            query: What to recall (semantic, not keyword match)
            memory: Memory data structure from memory_loader
            time_range_days: How far back to search (for display purposes)

        Returns:
            RLMResult with findings and sources
        """
        task_type = f"""Recall information from long-term memory.

Query: {query}
Time range: Last {time_range_days} days

Search through the memory entries to find information relevant to this query.
Use semantic understanding (via llm_query) to identify relevant content that
may not match exact keywords."""

        return self._run_session(query, memory, task_type)

    def analyze(self, query: str, memory: dict, time_range_days: int = 365) -> RLMResult:
        """
        Deep analysis of memory patterns.

        Args:
            query: What pattern to analyze
            memory: Memory data structure from memory_loader
            time_range_days: Analysis window (for display purposes)

        Returns:
            RLMResult with analysis findings
        """
        task_type = f"""Analyze patterns and trends in long-term memory.

Query: {query}
Time range: Last {time_range_days} days

Look for patterns, trends, recurring themes, and evolution over time.
Aggregate information across multiple entries to provide insights."""

        return self._run_session(query, memory, task_type)

    def detect_temporal(self, memory: dict, granularity: str = "daily") -> RLMResult:
        """
        Detect time-based patterns in memory.

        Args:
            memory: Memory data structure from memory_loader
            granularity: "daily", "weekly", or "seasonal"

        Returns:
            RLMResult with temporal patterns found
        """
        granularity_prompts = {
            "daily": """Focus on patterns that occur at specific times of day:
- Morning routines (6am-10am)
- Work patterns (9am-6pm)
- Evening activities (6pm-10pm)
- Night owl patterns (10pm-2am)

Look for activities, topics, or behaviors that cluster around certain times.""",

            "weekly": """Focus on patterns that occur on specific days of the week:
- Weekday vs weekend differences
- Monday patterns (planning, fresh starts)
- Friday patterns (wrapping up, social)
- Sunday patterns (preparation, reflection)

Look for topics or activities that appear more on certain days.""",

            "seasonal": """Focus on longer-term cycles:
- Monthly patterns (beginning/end of month)
- Quarterly patterns (review periods)
- Seasonal variations (energy, focus, interests)

Look for themes that wax and wane over weeks or months."""
        }

        task_type = f"""Detect temporal patterns in long-term memory.

Granularity: {granularity}

{granularity_prompts.get(granularity, granularity_prompts["daily"])}

## Analysis Strategy
1. Parse timestamps from entries (date and time fields)
2. Group entries by time period
3. Use statistics module for frequency analysis
4. Use llm_query() to identify what topics cluster together

## Expected Output Format
Return a JSON-formatted list of patterns:
```
[
    {{"description": "...", "time_window": {{"start": "08:00", "end": "09:00"}}, "evidence_count": N}},
    ...
]
```

Call FINAL() with the JSON list of detected patterns."""

        return self._run_session(f"Detect {granularity} temporal patterns", memory, task_type)

    def correlate(self, memory: dict, item_types: list = None) -> RLMResult:
        """
        Find correlations between different types of memory items.

        Args:
            memory: Memory data structure from memory_loader
            item_types: Optional list of types to focus on (e.g., ["concern", "behavior"])

        Returns:
            RLMResult with correlations found
        """
        type_focus = ""
        if item_types:
            type_focus = f"\nFocus on correlations involving: {', '.join(item_types)}"

        task_type = f"""Find correlations between different types of items in memory.
{type_focus}

## Correlation Types to Look For
1. **Co-occurrence**: Things that appear together on the same day
   - Example: "deadline mentions" often appear with "stress mentions"

2. **Causal/Temporal**: One thing tends to follow another
   - Example: "poor sleep" is often followed by "low energy" next day

3. **Inverse**: When one increases, the other decreases
   - Example: "social activity" and "solitary creative work" rarely appear together

## Analysis Strategy
1. Extract key themes/topics from entries using llm_query()
2. Build a co-occurrence matrix by date
3. Look for patterns where items appear together more often than random
4. Consider time-lagged correlations (1-3 day delays)

## Expected Output Format
Return a JSON-formatted list of correlations:
```
[
    {{
        "type": "co_occurrence",
        "items": [{{"type": "concern", "pattern": "deadline"}}, {{"type": "behavior", "pattern": "late nights"}}],
        "description": "Deadline pressure correlates with late night work",
        "lag_days": 0
    }},
    ...
]
```

Call FINAL() with the JSON list of detected correlations."""

        return self._run_session("Find correlations in memory patterns", memory, task_type)

    def detect_trajectories(self, memory: dict, subjects: list = None) -> RLMResult:
        """
        Detect how goals, concerns, or interests evolve over time.

        Args:
            memory: Memory data structure from memory_loader
            subjects: Optional list of subjects to track (e.g., ["career", "health"])

        Returns:
            RLMResult with trajectories found
        """
        subject_focus = ""
        if subjects:
            subject_focus = f"\nFocus on tracking: {', '.join(subjects)}"

        task_type = f"""Detect trajectories - how goals, concerns, and interests evolve over time.
{subject_focus}

## Trajectory Types
1. **Goal Evolution**: How goals clarify, expand, or get resolved
   - Example: "wanting a new job" → "exploring tech roles" → "preparing for ML interviews"

2. **Concern Evolution**: How worries intensify, diminish, or transform
   - Example: "general anxiety" → "specific deadline worry" → "resolved after delivery"

3. **Interest Shift**: How interests develop or fade
   - Example: "casual interest in AI" → "deep diving into LLMs" → "building AI projects"

## Trajectory Directions
- **clarifying**: Getting more specific and focused
- **expanding**: Broadening scope or ambition
- **resolving**: Moving toward completion/resolution
- **intensifying**: Becoming more urgent or important
- **diminishing**: Fading in importance or attention

## Analysis Strategy
1. Identify recurring subjects across entries using llm_query()
2. Track how the language/framing of each subject changes over time
3. Identify stage transitions (dates when framing shifted)
4. Determine overall direction

## Expected Output Format
Return a JSON-formatted list of trajectories:
```
[
    {{
        "type": "goal_evolution",
        "subject": "career focus",
        "stages": [
            {{"date": "2025-11-01", "state": "considering change"}},
            {{"date": "2025-12-15", "state": "exploring options"}},
            {{"date": "2026-01-10", "state": "focused on AI/ML"}}
        ],
        "direction": "clarifying"
    }},
    ...
]
```

Call FINAL() with the JSON list of detected trajectories."""

        return self._run_session("Detect evolution trajectories", memory, task_type)

    def discover_patterns(
        self,
        memory: dict,
        pattern_types: list = None,
        existing_patterns: dict = None
    ) -> dict:
        """
        Orchestrate multi-pass pattern discovery.

        This is the main entry point for pattern discovery during consolidation.
        It runs multiple specialized passes and aggregates results.

        Args:
            memory: Memory data structure from memory_loader
            pattern_types: Types to discover (defaults to ["temporal", "correlation", "trajectory"])
            existing_patterns: Previously discovered patterns to build on

        Returns:
            Dict with discovered patterns by type:
            {
                "temporal": [...],
                "correlations": [...],
                "trajectories": [...],
                "hypotheses": [...]  # New hypotheses generated
            }
        """
        if pattern_types is None:
            pattern_types = ["temporal", "correlation", "trajectory"]

        results = {
            "temporal": [],
            "correlations": [],
            "trajectories": [],
            "hypotheses": []
        }

        # Run temporal detection
        if "temporal" in pattern_types:
            for granularity in ["daily", "weekly"]:
                try:
                    result = self.detect_temporal(memory, granularity)
                    if result.findings and not result.error:
                        patterns = self._parse_json_findings(result.findings)
                        for p in patterns:
                            p["granularity"] = granularity
                        results["temporal"].extend(patterns)
                except Exception:
                    pass  # Continue with other passes

        # Run correlation detection
        if "correlation" in pattern_types:
            try:
                result = self.correlate(memory)
                if result.findings and not result.error:
                    correlations = self._parse_json_findings(result.findings)
                    results["correlations"].extend(correlations)
            except Exception:
                pass

        # Run trajectory detection
        if "trajectory" in pattern_types:
            try:
                result = self.detect_trajectories(memory)
                if result.findings and not result.error:
                    trajectories = self._parse_json_findings(result.findings)
                    results["trajectories"].extend(trajectories)
            except Exception:
                pass

        return results

    def _parse_json_findings(self, findings: str) -> list:
        """Parse JSON from RLM findings string."""
        import json as json_module

        # Try to extract JSON array from the findings
        findings = findings.strip()

        # If it starts with [ and ends with ], try direct parse
        if findings.startswith("[") and findings.endswith("]"):
            try:
                return json_module.loads(findings)
            except json_module.JSONDecodeError:
                pass

        # Try to find JSON array in the text
        import re
        match = re.search(r'\[[\s\S]*\]', findings)
        if match:
            try:
                return json_module.loads(match.group(0))
            except json_module.JSONDecodeError:
                pass

        return []
