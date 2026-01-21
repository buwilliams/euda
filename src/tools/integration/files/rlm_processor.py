"""
RLM Processor - Process files using RLM to extract dates and format content.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from ....agent.rlm.repl import REPLEnvironment, ExecutionResult
from ....llms.base import get_client, UnifiedClient


@dataclass
class StoreResult:
    """Result of processing a file."""
    file: str  # Filename
    date: str  # Extracted date (YYYY-MM-DD)
    date_source: str  # How date was determined: content, filename, llm, mtime
    content: str  # Content to store
    source: str  # Source label for memory entry
    error: Optional[str] = None


@dataclass
class ProcessingResult:
    """Result of RLM file processing session."""
    results: List[StoreResult] = field(default_factory=list)
    iterations: int = 0
    sub_calls: int = 0
    error: Optional[str] = None


def _build_store_system_prompt() -> str:
    """Build the system prompt for file storage RLM sessions."""
    return r'''You are processing files to store in long-term memory.

## Available Variables
- `files['items']`: List of files with {path, name, content, size, mtime, extension}
- `files['metadata']`: {total_files, total_chars, extensions}

## Available Functions
- `llm_query(prompt)`: Ask for semantic analysis (use for date extraction when patterns fail)
- `print()`: Output information for debugging
- `FINAL(json_string)`: Return structured results as JSON string

## Available Modules
- `re`: Regular expressions
- `json`: JSON parsing
- `datetime`: Date/time utilities

## Your Task
For each file, determine:
1. **date**: When was this content created/written?
   - First: Look for dates IN the content (headers, metadata, journal entries)
   - Second: Parse date from filename (e.g., 2024-01-15, journal_20240115, 2024_01_15)
   - Third: Use file mtime as fallback
   - Use llm_query() only for ambiguous content that needs semantic understanding

2. **content**: The text to store (preserve the original, but you may clean up minor formatting)

3. **source**: Label for attribution (use "upload:" + filename)

## Output Format
Call FINAL() with a JSON array string:
```python
import json
results = [
    {"file": "journal-2024-01-15.md", "date": "2024-01-15", "date_source": "filename", "content": "...", "source": "upload:journal-2024-01-15.md"},
    ...
]
FINAL(json.dumps(results))
```

## Example Code
```python
import re
import json
from datetime import datetime

results = []
for f in files['items']:
    content = f['content']
    date = None
    date_source = None

    # Pattern 1: Date header in content (# 2024-01-15 or Date: 2024-01-15)
    match = re.search(r'^(?:#\s*)?(?:Date:?\s*)?(\d{4}-\d{2}-\d{2})', content, re.M)
    if match:
        date = match.group(1)
        date_source = 'content'

    # Pattern 2: Date in filename (2024-01-15, 20240115, 2024_01_15)
    if not date:
        # Standard format: 2024-01-15
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', f['name'])
        if match:
            date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
            date_source = 'filename'

    if not date:
        # Compact format: 20240115
        match = re.search(r'(\d{4})(\d{2})(\d{2})', f['name'])
        if match:
            y, m, d = match.groups()
            if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
                date = f"{y}-{m}-{d}"
                date_source = 'filename'

    if not date:
        # Underscore format: 2024_01_15
        match = re.search(r'(\d{4})_(\d{2})_(\d{2})', f['name'])
        if match:
            date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
            date_source = 'filename'

    # Pattern 3: Use llm_query for complex cases with substantial content
    if not date and len(content) > 100:
        try:
            response = llm_query(f"Extract the date this was written. Return ONLY a date in YYYY-MM-DD format, nothing else. If no date is apparent, return 'unknown'.\\n\\n{content[:1000]}")
            if re.match(r'\d{4}-\d{2}-\d{2}', response.strip()):
                date = response.strip()[:10]
                date_source = 'llm'
        except:
            pass

    # Fallback to mtime
    if not date:
        date = datetime.fromtimestamp(f['mtime']).strftime('%Y-%m-%d')
        date_source = 'mtime'

    results.append({
        "file": f['name'],
        "date": date,
        "date_source": date_source,
        "content": content[:40000],  # Truncate very long content
        "source": f"upload:{f['name']}"
    })

FINAL(json.dumps(results))
```

Write Python code to process the files. You may adapt the example based on what you observe.
After each code block, I will show you the output so you can continue or fix issues.
When done, call FINAL() with the JSON results.'''


class StoreRLMClient:
    """RLM client for file storage processing."""

    def __init__(self, llm_client: UnifiedClient = None):
        self.client = llm_client or get_client()
        self.max_iterations = 15
        self._sub_call_count = 0
        self._iteration_count = 0

    def _create_llm_query_fn(self) -> callable:
        """Create the llm_query function for the REPL."""
        def llm_query(prompt: str) -> str:
            self._sub_call_count += 1
            try:
                response = self.client.create(
                    max_tokens=500,
                    system="You are extracting information from text. Be concise and direct. "
                           "Return only the requested information, no explanations.",
                    messages=[{"role": "user", "content": prompt}],
                    agent_id="rlm-store",
                    track_cost=True
                )
                for block in response.content:
                    if hasattr(block, 'text'):
                        return block.text
                return "[No response]"
            except Exception as e:
                return f"[Error: {str(e)}]"

        return llm_query

    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract Python code blocks from LLM response."""
        pattern = r'```(?:python)?\s*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        return matches if matches else []

    def _parse_results(self, json_str: str) -> List[StoreResult]:
        """Parse JSON results into StoreResult objects."""
        import json as json_module

        try:
            data = json_module.loads(json_str)
            results = []
            for item in data:
                results.append(StoreResult(
                    file=item.get("file", "unknown"),
                    date=item.get("date", ""),
                    date_source=item.get("date_source", "unknown"),
                    content=item.get("content", ""),
                    source=item.get("source", "upload")
                ))
            return results
        except (json_module.JSONDecodeError, TypeError) as e:
            return [StoreResult(
                file="",
                date="",
                date_source="",
                content="",
                source="",
                error=f"Failed to parse results: {e}"
            )]


def process_with_rlm(files_data: dict) -> ProcessingResult:
    """Process files using RLM.

    Args:
        files_data: Dict from files_to_rlm_format() with items and metadata

    Returns:
        ProcessingResult with extracted data for each file
    """
    client = StoreRLMClient()
    client._sub_call_count = 0
    client._iteration_count = 0

    # Create REPL with files instead of memory
    llm_query_fn = client._create_llm_query_fn()

    # Custom REPL environment that uses 'files' instead of 'memory'
    repl = REPLEnvironment({}, llm_query_fn)
    repl.globals['files'] = files_data

    # Build conversation
    system_prompt = _build_store_system_prompt()
    messages = [{"role": "user", "content": f"Process {files_data['metadata']['total_files']} files."}]

    # Iteration loop
    while client._iteration_count < client.max_iterations:
        client._iteration_count += 1

        try:
            response = client.client.create(
                max_tokens=4000,
                system=system_prompt,
                messages=messages,
                agent_id="rlm-store",
                track_cost=True
            )
        except Exception as e:
            return ProcessingResult(
                error=f"LLM call failed: {str(e)}",
                iterations=client._iteration_count,
                sub_calls=client._sub_call_count
            )

        # Extract response text
        assistant_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                assistant_text += block.text

        messages.append({"role": "assistant", "content": assistant_text})

        # Extract and execute code blocks
        code_blocks = client._extract_code_blocks(assistant_text)

        if not code_blocks:
            # Check for FINAL in text
            match = re.search(r'FINAL\(["\'](.+?)["\']\)', assistant_text)
            if match:
                results = client._parse_results(match.group(1))
                return ProcessingResult(
                    results=results,
                    iterations=client._iteration_count,
                    sub_calls=client._sub_call_count
                )

            messages.append({
                "role": "user",
                "content": "Please write Python code to process the files. "
                          "Wrap your code in ```python ... ``` blocks."
            })
            continue

        # Execute code blocks
        all_output = []
        final_result = None

        for code in code_blocks:
            result = repl.execute(code, timeout=60)

            if result.output:
                all_output.append(result.output)
            if result.error:
                all_output.append(f"[Error]: {result.error}")
            if result.final_answer:
                final_result = result
                break

        combined_output = '\n'.join(all_output)
        if len(combined_output) > 10000:
            combined_output = combined_output[:10000] + "\n[Output truncated...]"

        # Check for final answer
        if final_result and final_result.final_answer:
            results = client._parse_results(final_result.final_answer)
            return ProcessingResult(
                results=results,
                iterations=client._iteration_count,
                sub_calls=client._sub_call_count
            )

        # Continue conversation
        messages.append({
            "role": "user",
            "content": f"Output:\n```\n{combined_output}\n```\n\n"
                      "Continue processing or call FINAL() with your JSON results."
        })

    # Max iterations reached
    return ProcessingResult(
        error="Max iterations reached",
        iterations=client._iteration_count,
        sub_calls=client._sub_call_count
    )
