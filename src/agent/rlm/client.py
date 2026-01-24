"""
RLM Client

Manages RLM sessions for memory access.
Based on the Recursive Language Models paper (arXiv:2512.24601v1).
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Callable

from .repl import REPLEnvironment, ExecutionResult
from ...llms.base import get_client, UnifiedClient
from ..cognition.metacognition.regulation import (
    get_progress_tracker,
    ProgressLimitExceeded,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_MAX_RECURSION_DEPTH,
)


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
    """Configuration for RLM REPL execution.

    Note: Iteration and recursion limits are handled by the regulation
    module's progress tracking system, not by this config.
    """
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
            execution_timeout_seconds=rlm_config.get("execution_timeout_seconds", 30),
            output_truncation_chars=rlm_config.get("output_truncation_chars", 10000)
        )
    except (json.JSONDecodeError, KeyError):
        return RLMConfig()


class RLMClient:
    """Manages RLM sessions for memory access.

    This client mediates all long-term memory access through a REPL environment
    where the LLM can write code to search, filter, and analyze memory entries.

    All LLM calls are attributed to the originating agent and tracked through
    the regulation module's token awareness and progress tracking systems.
    """

    def __init__(self, llm_client: UnifiedClient = None, agent_id: str = "user"):
        """
        Initialize the RLM client.

        Args:
            llm_client: LLM client for making calls (uses default if not provided)
            agent_id: ID of the agent using this client (calls attributed to this agent)
        """
        self.client = llm_client or get_client()
        self.agent_id = agent_id
        self.config = _load_rlm_config()
        self._progress_tracker = get_progress_tracker()

        # Track session state
        self._sub_call_count = 0
        self._iteration_count = 0
        self._session_id: Optional[str] = None

    def _create_llm_query_fn(self, session_id: str) -> Callable[[str], str]:
        """Create the llm_query function for the REPL.

        Args:
            session_id: Progress tracking session ID

        Returns:
            Function that makes sub-LLM calls
        """
        def llm_query(prompt: str) -> str:
            """Query the LLM for semantic analysis."""
            # Check recursion depth via progress tracker
            try:
                self._progress_tracker.enter_recursion(session_id)
            except ProgressLimitExceeded:
                return "[Error: Maximum recursion depth reached]"

            self._sub_call_count += 1

            try:
                response = self.client.create(
                    max_tokens=2000,
                    system="You are a helpful assistant analyzing memory content. "
                           "Provide concise, factual analysis. Be direct and brief.",
                    messages=[{"role": "user", "content": prompt}],
                    agent_id=self.agent_id,
                    track_cost=True
                )

                # Extract text from response
                for block in response.content:
                    if hasattr(block, 'text'):
                        return block.text

                return "[No response from LLM]"

            except Exception as e:
                return f"[Error in llm_query: {str(e)}]"
            finally:
                self._progress_tracker.exit_recursion(session_id)

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

        # Start progress tracking session
        session_id = self._progress_tracker.start_session(
            agent_id=self.agent_id,
            max_iterations=DEFAULT_MAX_ITERATIONS,
            max_recursion_depth=DEFAULT_MAX_RECURSION_DEPTH,
            session_type="rlm"
        )
        self._session_id = session_id

        try:
            return self._run_session_loop(query, memory, task_type, session_id)
        finally:
            self._progress_tracker.end_session(session_id)
            self._session_id = None

    def _run_session_loop(self, query: str, memory: dict, task_type: str,
                          session_id: str) -> RLMResult:
        """Internal session loop with progress tracking.

        Args:
            query: The user's query
            memory: Memory data structure
            task_type: Description of the task for the system prompt
            session_id: Progress tracking session ID

        Returns:
            RLMResult with findings
        """
        # Create REPL environment
        llm_query_fn = self._create_llm_query_fn(session_id)
        repl = REPLEnvironment(memory, llm_query_fn)

        # Build conversation
        system_prompt = self._build_system_prompt(task_type)
        messages = [{"role": "user", "content": f"Query: {query}"}]

        # Track sources for attribution
        sources = []

        # Iteration loop - controlled by progress tracker
        while True:
            # Increment and check iteration limit
            try:
                self._iteration_count = self._progress_tracker.increment(session_id)
            except ProgressLimitExceeded:
                return RLMResult(
                    query=query,
                    findings="Maximum iterations reached without finding an answer.",
                    sources=sources,
                    iterations=self._iteration_count,
                    sub_calls=self._sub_call_count,
                    error="Max iterations reached"
                )

            # Get LLM response
            try:
                response = self.client.create(
                    max_tokens=4000,
                    system=system_prompt,
                    messages=messages,
                    agent_id=self.agent_id,
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
        Deep analysis of memory content.

        Args:
            query: What to analyze
            memory: Memory data structure from memory_loader
            time_range_days: Analysis window (for display purposes)

        Returns:
            RLMResult with analysis findings
        """
        task_type = f"""Analyze long-term memory content.

Query: {query}
Time range: Last {time_range_days} days

Look for trends, recurring themes, and evolution over time.
Aggregate information across multiple entries to provide insights."""

        return self._run_session(query, memory, task_type)

    def extract_recent(self, memory: dict, days: int = 90) -> RLMResult:
        """
        Extract currently active/relevant items from long-term memory.

        This derives a "short-term view" from long-term memory by finding
        items that are currently active: recent goals, ongoing concerns,
        important people, upcoming events, etc.

        Args:
            memory: Memory data structure from memory_loader
            days: How many days back to consider "recent" (default 90)

        Returns:
            RLMResult with JSON list of active items:
            [
                {"type": "goal", "description": "...", "status": "active"},
                {"type": "concern", "description": "...", "urgency": "high"},
                {"type": "person", "name": "...", "relationship": "..."},
                {"type": "event", "description": "...", "date": "YYYY-MM-DD"}
            ]
        """
        task_type = f"""Extract currently active/relevant items from recent memory.

Time window: Last {days} days

Find items that are CURRENTLY relevant - not historical facts, but active concerns:

1. **Active Goals**: Goals being worked on or recently mentioned
2. **Current Concerns**: Worries or issues that are unresolved
3. **Important People**: People mentioned recently (relationships, collaborators)
4. **Upcoming Events**: Scheduled events, deadlines, or anticipated happenings
5. **Active Ideas**: Ideas being explored or considered

## Output Format
Return a JSON array of active items:
```json
[
    {{"type": "goal", "description": "...", "status": "active|progressing|stalled"}},
    {{"type": "concern", "description": "...", "urgency": "high|medium|low"}},
    {{"type": "person", "name": "...", "context": "..."}},
    {{"type": "event", "description": "...", "date": "YYYY-MM-DD", "nature": "deadline|appointment|milestone"}},
    {{"type": "idea", "description": "...", "stage": "exploring|developing|implementing"}}
]
```

## Strategy
1. Scan recent entries for mentions of goals, plans, concerns
2. Use llm_query() to determine if items are still active
3. Filter out resolved items or historical mentions
4. Return only items relevant to current context

Call FINAL() with the JSON array when done."""

        return self._run_session(f"Extract active items from last {days} days", memory, task_type)

    def extract_identity(self, memory: dict, current_identity: str) -> RLMResult:
        """
        Analyze memory for identity updates not yet captured.

        Compares memory patterns against the current identity document
        and identifies NEW patterns, learnings, or changes that should
        be incorporated into the identity.

        Args:
            memory: Memory data structure from memory_loader
            current_identity: Current identity.md content

        Returns:
            RLMResult with structured identity updates:
            {
                "sections": {
                    "stable_attractors": ["new attractor 1", ...],
                    "interests": ["emerging interest", ...],
                    "notable_events": ["significant event", ...],
                    ...
                },
                "reasoning": "Why these updates are warranted"
            }
        """
        # Truncate identity if too long for context
        identity_preview = current_identity[:4000] if len(current_identity) > 4000 else current_identity

        task_type = f"""Analyze memory for identity updates not yet in the current identity document.

## Current Identity (for reference)
```
{identity_preview}
```

## Your Task
Compare recent memory against this identity and find:

1. **NEW patterns** not reflected in identity - behaviors, preferences, values that have emerged
2. **Changed priorities** - shifts in focus or interests
3. **Notable events** - significant happenings that shaped who this person is
4. **New stable attractors** - topics/activities they consistently return to
5. **Emerging interests** - new areas of curiosity or engagement

## Important Guidelines
- Only suggest ADDITIONS, not removals
- Focus on patterns with EVIDENCE in memory (multiple mentions, sustained over time)
- Don't repeat what's already in the identity
- Be specific and actionable

## Output Format
Return a JSON object with section updates:
```json
{{
    "sections": {{
        "stable_attractors": ["specific new attractor with evidence"],
        "interests": ["emerging interest seen in memory"],
        "notable_events": ["significant event: brief description"],
        "wants_and_fears": ["newly apparent want or fear"],
        "biographical_information": ["factual information learned"]
    }},
    "reasoning": "Brief explanation of why these updates are warranted based on memory evidence"
}}
```

Only include sections that have genuine updates. Empty sections can be omitted.

## Strategy
1. First scan memory for recurring themes, topics, and patterns
2. Compare against current identity to find what's NEW
3. Use llm_query() to validate patterns have sufficient evidence
4. Generate specific, evidence-backed updates

Call FINAL() with the JSON object when done."""

        return self._run_session("Extract identity updates from memory", memory, task_type)

    def process_conversation(self, conversation: str, context: str = "") -> RLMResult:
        """
        Analyze a conversation for items worth preserving in long-term memory.

        This processes a single conversation exchange to determine if
        anything significant was mentioned that should be tracked.

        Args:
            conversation: The conversation text to analyze
            context: Optional context (user identity, recent memory items)

        Returns:
            RLMResult with items to remember:
            [
                {"type": "goal", "description": "...", "significance": "..."},
                ...
            ]
        """
        # Build a minimal memory structure for the REPL
        # (This method doesn't use full memory - just the conversation)
        minimal_memory = {
            "entries": [{"date": "today", "content": conversation}],
            "by_date": {"today": conversation},
            "metadata": {"total_entries": 1, "total_chars": len(conversation)}
        }

        context_section = f"\n## Context\n{context}" if context else ""

        task_type = f"""Analyze this conversation for significant items worth remembering.
{context_section}

## Item Types to Look For
- **goal**: Stated objectives, plans, or aspirations
- **concern**: Worries, problems, or challenges mentioned
- **person**: People mentioned (names, relationships)
- **idea**: Concepts being explored or considered
- **learning**: New knowledge or insights gained
- **event**: Upcoming or past events mentioned (with dates if given)

## Output Format
Return a JSON array of items (or empty array if nothing significant):
```json
[
    {{"type": "goal", "description": "...", "date_expected": "YYYY-MM-DD or null"}},
    {{"type": "concern", "description": "..."}},
    {{"type": "person", "name": "...", "context": "..."}},
    {{"type": "event", "description": "...", "date": "YYYY-MM-DD"}}
]
```

## Guidelines
- Only extract SIGNIFICANT items worth tracking over time
- Skip routine conversation filler
- Be specific in descriptions
- Include dates when explicitly mentioned

Call FINAL() with the JSON array (can be empty [])."""

        return self._run_session("Extract significant items from conversation", minimal_memory, task_type)
