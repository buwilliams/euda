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
