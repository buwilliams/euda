"""
Unit tests for RLM (Recursive Language Model) Client.

Tests for src/agent/rlm/client.py including:
- RLM session execution
- Code block extraction
- Memory querying
- Sub-LLM calls

Spec: Based on arXiv:2512.24601v1 - Recursive Language Models
"""

import pytest
from unittest.mock import MagicMock, patch
import json

from tests.fixtures.llm import MockLLMClient, MockResponse


class TestRLMConfig:
    """Test RLM configuration loading.

    Note: Iteration and recursion limits are now handled by the regulation
    module's progress tracking system, not by RLMConfig.
    """

    def test_default_config_values(self):
        """RLMConfig has sensible defaults for REPL execution."""
        from src.agent.rlm.client import RLMConfig

        config = RLMConfig()

        # Only REPL-related settings remain in config
        assert config.execution_timeout_seconds == 30
        assert config.output_truncation_chars == 10000

    def test_load_config_returns_defaults_when_no_file(self):
        """_load_rlm_config returns defaults when config file doesn't exist."""
        from src.agent.rlm.client import _load_rlm_config

        # When config file doesn't exist, should return defaults
        result = _load_rlm_config()

        assert result.execution_timeout_seconds > 0
        assert result.output_truncation_chars > 0


class TestRLMClient:
    """Test RLMClient initialization and basic operations."""

    def test_client_initialization(self):
        """RLMClient initializes with default config."""
        from src.agent.rlm.client import RLMClient

        mock = MockLLMClient.simple()

        with mock.patch():
            client = RLMClient(agent_id="test")

        assert client.agent_id == "test"
        assert client.config is not None

    def test_client_uses_provided_llm_client(self):
        """RLMClient uses provided LLM client."""
        from src.agent.rlm.client import RLMClient

        mock_llm = MagicMock()
        client = RLMClient(llm_client=mock_llm, agent_id="test")

        assert client.client == mock_llm


class TestCodeBlockExtraction:
    """Test extracting Python code from LLM responses."""

    def test_extract_python_code_blocks(self):
        """Extract ```python ... ``` blocks."""
        from src.agent.rlm.client import RLMClient

        mock = MockLLMClient.simple()
        with mock.patch():
            client = RLMClient(agent_id="test")

        text = '''Let me analyze the memory.

```python
entries = memory['entries']
print(len(entries))
```

That should show us the count.'''

        blocks = client._extract_code_blocks(text)

        assert len(blocks) == 1
        assert "entries = memory['entries']" in blocks[0]
        assert "print(len(entries))" in blocks[0]

    def test_extract_multiple_code_blocks(self):
        """Extract multiple code blocks."""
        from src.agent.rlm.client import RLMClient

        mock = MockLLMClient.simple()
        with mock.patch():
            client = RLMClient(agent_id="test")

        text = '''```python
x = 1
```

And then:

```python
y = 2
FINAL(str(x + y))
```'''

        blocks = client._extract_code_blocks(text)

        assert len(blocks) == 2

    def test_extract_unmarked_code_blocks(self):
        """Extract ``` ... ``` blocks without language marker."""
        from src.agent.rlm.client import RLMClient

        mock = MockLLMClient.simple()
        with mock.patch():
            client = RLMClient(agent_id="test")

        text = '''```
print("hello")
```'''

        blocks = client._extract_code_blocks(text)

        assert len(blocks) == 1

    def test_no_code_blocks_returns_empty(self):
        """Returns empty list when no code blocks present."""
        from src.agent.rlm.client import RLMClient

        mock = MockLLMClient.simple()
        with mock.patch():
            client = RLMClient(agent_id="test")

        text = "Just some text without any code."

        blocks = client._extract_code_blocks(text)

        assert blocks == []


class TestOutputTruncation:
    """Test output truncation for long responses."""

    def test_truncate_long_output(self):
        """Long output is truncated."""
        from src.agent.rlm.client import RLMClient, RLMConfig

        mock = MockLLMClient.simple()
        with mock.patch():
            client = RLMClient(agent_id="test")
            client.config = RLMConfig(output_truncation_chars=100)

        long_text = "x" * 200

        result = client._truncate_output(long_text)

        assert len(result) < 200
        assert "[Output truncated...]" in result

    def test_short_output_not_truncated(self):
        """Short output is not modified."""
        from src.agent.rlm.client import RLMClient

        mock = MockLLMClient.simple()
        with mock.patch():
            client = RLMClient(agent_id="test")

        short_text = "Hello world"

        result = client._truncate_output(short_text)

        assert result == short_text


class TestRLMSession:
    """Test RLM session execution with mocked LLM."""

    def _create_memory(self):
        """Create sample memory structure."""
        return {
            "entries": [
                {"date": "2025-01-01", "content": "Started new project", "source": "test"},
                {"date": "2025-01-15", "content": "Met with Alice about goals", "source": "test"},
                {"date": "2025-01-20", "content": "Completed milestone 1", "source": "test"}
            ],
            "by_date": {
                "2025-01-01": "# 2025-01-01\n\nStarted new project",
                "2025-01-15": "# 2025-01-15\n\nMet with Alice about goals",
                "2025-01-20": "# 2025-01-20\n\nCompleted milestone 1"
            },
            "metadata": {
                "total_entries": 3,
                "total_chars": 100,
                "date_range": {"start": "2025-01-01", "end": "2025-01-20"}
            }
        }

    def test_recall_with_immediate_final(self):
        """Recall returns immediately when LLM provides FINAL() in first response."""
        from src.agent.rlm.client import RLMClient

        # LLM response with code that calls FINAL
        mock = MockLLMClient.simple(text='''```python
entries = memory['entries']
FINAL("Found 3 entries in memory")
```''')

        with mock.patch():
            client = RLMClient(agent_id="test")
            memory = self._create_memory()
            result = client.recall("What's in memory?", memory)

        assert result.error is None or result.findings
        assert result.iterations >= 1

    def test_recall_handles_llm_error(self):
        """Recall handles LLM call failures gracefully."""
        from src.agent.rlm.client import RLMClient

        mock = MockLLMClient.simple()

        with mock.patch():
            # Make the mock raise an error
            with patch.object(mock, 'create', side_effect=Exception("API Error")):
                client = RLMClient(llm_client=mock, agent_id="test")
                memory = self._create_memory()
                result = client.recall("Test query", memory)

        assert result.error is not None
        assert "LLM call failed" in result.error or "API Error" in result.error

    def test_recall_respects_max_iterations(self):
        """Recall stops after max_iterations (via progress tracker)."""
        from src.agent.rlm.client import RLMClient
        from src.agent.cognition.metacognition.regulation import get_progress_tracker

        # LLM that never produces FINAL
        mock = MockLLMClient.simple(text='''```python
print("Still searching...")
```''')

        with mock.patch():
            client = RLMClient(agent_id="test")
            memory = self._create_memory()
            result = client.recall("Endless query", memory)

        # Progress tracker enforces max iterations (default 20)
        assert result.iterations <= 20
        assert "Max iterations" in (result.error or "") or result.iterations > 0

    def test_recall_tracks_iterations(self):
        """Recall tracks iteration count."""
        from src.agent.rlm.client import RLMClient

        mock = MockLLMClient.simple(text='FINAL("answer")')

        with mock.patch():
            client = RLMClient(agent_id="test")
            memory = self._create_memory()
            result = client.recall("Quick query", memory)

        assert result.iterations >= 1


class TestSubLLMCalls:
    """Test RLM sub-LLM calls (llm_query function).

    Note: The llm_query function now takes a session_id instead of depth,
    and recursion depth is tracked via the progress tracker.
    """

    def test_llm_query_makes_sub_call(self):
        """llm_query function makes LLM call for semantic analysis."""
        from src.agent.rlm.client import RLMClient
        from src.agent.cognition.metacognition.regulation import get_progress_tracker

        mock_llm = MagicMock()
        mock_llm.create.return_value = MagicMock(
            content=[MagicMock(type="text", text="Analysis: This mentions goals")]
        )

        client = RLMClient(llm_client=mock_llm, agent_id="test")

        # Create a progress tracking session for the test
        tracker = get_progress_tracker()
        session_id = tracker.start_session(agent_id="test", session_type="test")

        try:
            llm_query = client._create_llm_query_fn(session_id)
            result = llm_query("Analyze this text for goals")

            assert mock_llm.create.called
            assert "Analysis" in result
        finally:
            tracker.end_session(session_id)

    def test_llm_query_respects_recursion_depth(self):
        """llm_query returns error when max recursion reached."""
        from src.agent.rlm.client import RLMClient
        from src.agent.cognition.metacognition.regulation import get_progress_tracker

        mock = MockLLMClient.simple()

        with mock.patch():
            client = RLMClient(agent_id="test")

            # Create a session with max_recursion_depth=1
            tracker = get_progress_tracker()
            session_id = tracker.start_session(
                agent_id="test",
                max_recursion_depth=1,
                session_type="test"
            )

            try:
                llm_query = client._create_llm_query_fn(session_id)

                # First call should succeed (enters depth 1)
                result1 = llm_query("First call")

                # Within that first call, another call would exceed depth
                # Simulate this by entering recursion again
                tracker.enter_recursion(session_id)  # Now at depth 2

                # Now next llm_query call should fail
                result2 = llm_query("Should fail")
                assert "Maximum recursion depth" in result2
            finally:
                tracker.end_session(session_id)

    def test_llm_query_counts_sub_calls(self):
        """llm_query increments sub_call_count."""
        from src.agent.rlm.client import RLMClient
        from src.agent.cognition.metacognition.regulation import get_progress_tracker

        mock = MockLLMClient.simple(text="Result")

        with mock.patch():
            client = RLMClient(agent_id="test")
            assert client._sub_call_count == 0

            # Create a session for the test
            tracker = get_progress_tracker()
            session_id = tracker.start_session(agent_id="test", session_type="test")

            try:
                llm_query = client._create_llm_query_fn(session_id)
                llm_query("First call")
                llm_query("Second call")
            finally:
                tracker.end_session(session_id)

        assert client._sub_call_count == 2

    def test_llm_query_handles_errors(self):
        """llm_query returns error message on exception."""
        from src.agent.rlm.client import RLMClient
        from src.agent.cognition.metacognition.regulation import get_progress_tracker

        mock = MockLLMClient.simple()

        with mock.patch():
            with patch.object(mock, 'create', side_effect=Exception("API failed")):
                client = RLMClient(llm_client=mock, agent_id="test")

                # Create a session for the test
                tracker = get_progress_tracker()
                session_id = tracker.start_session(agent_id="test", session_type="test")

                try:
                    llm_query = client._create_llm_query_fn(session_id)
                    result = llm_query("Should fail")
                finally:
                    tracker.end_session(session_id)

        assert "[Error" in result


class TestRLMResult:
    """Test RLMResult dataclass."""

    def test_rlm_result_fields(self):
        """RLMResult has expected fields."""
        from src.agent.rlm.client import RLMResult

        result = RLMResult(
            query="test query",
            findings="Found something",
            sources=[{"date": "2025-01-01", "content": "test"}],
            iterations=5,
            sub_calls=2,
            error=None
        )

        assert result.query == "test query"
        assert result.findings == "Found something"
        assert len(result.sources) == 1
        assert result.iterations == 5
        assert result.sub_calls == 2
        assert result.error is None

    def test_rlm_result_defaults(self):
        """RLMResult has sensible defaults."""
        from src.agent.rlm.client import RLMResult

        result = RLMResult(query="test", findings="answer")

        assert result.sources == []
        assert result.iterations == 0
        assert result.sub_calls == 0
        assert result.error is None


class TestSystemPromptBuilding:
    """Test RLM system prompt generation."""

    def test_system_prompt_includes_task(self):
        """System prompt includes task description."""
        from src.agent.rlm.client import RLMClient

        mock = MockLLMClient.simple()

        with mock.patch():
            client = RLMClient(agent_id="test")
            prompt = client._build_system_prompt("Find all goals mentioned")

        assert "Find all goals mentioned" in prompt

    def test_system_prompt_includes_instructions(self):
        """System prompt includes REPL instructions."""
        from src.agent.rlm.client import RLMClient

        mock = MockLLMClient.simple()

        with mock.patch():
            client = RLMClient(agent_id="test")
            prompt = client._build_system_prompt("Any task")

        assert "memory['entries']" in prompt
        assert "FINAL" in prompt
        assert "llm_query" in prompt
