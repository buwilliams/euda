"""
MockLLMClient - Mock LLM client for testing.

Provides a UnifiedClient-compatible interface that returns pre-recorded
responses instead of making real API calls. Supports:
- Loading responses from JSON fixtures
- Matching requests by scenario/pattern
- Recording call history for assertions
"""

import json
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
from unittest.mock import patch


FIXTURES_DIR = Path(__file__).parent / "responses"


# Local versions of LLM types to avoid circular imports
# These mirror src.llms.base but are self-contained

@dataclass
class Usage:
    """Token usage statistics."""
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0


@dataclass
class TextBlock:
    """Text content block."""
    type: str = "text"
    text: str = ""


@dataclass
class ToolUseBlock:
    """Tool use content block."""
    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: dict = None


@dataclass
class UnifiedResponse:
    """Unified response format across providers."""
    content: list  # List of TextBlock or ToolUseBlock
    stop_reason: str  # "end_turn", "tool_use", etc.
    usage: Usage


@dataclass
class RecordedCall:
    """Record of a mocked LLM call for test assertions."""
    max_tokens: int
    system: str
    messages: list
    tools: Optional[list]
    agent_id: str
    job_id: Optional[str]
    response: UnifiedResponse


@dataclass
class MockResponse:
    """A pre-configured response for the mock client."""
    # Matching criteria (all optional, more specific = higher priority)
    scenario: str = ""  # Named scenario (e.g., "planning", "append")
    system_contains: str = ""  # Match if system prompt contains this
    message_contains: str = ""  # Match if any message contains this
    agent_id_pattern: str = ""  # Regex pattern for agent_id

    # Response data
    text: str = ""  # Text response content
    tool_calls: List[Dict] = field(default_factory=list)  # Tool use blocks
    stop_reason: str = "end_turn"
    input_tokens: int = 100
    output_tokens: int = 50
    cached_input_tokens: int = 0

    def matches(self, system: str, messages: list, agent_id: str) -> int:
        """Check if this response matches the request.

        Returns:
            Priority score (higher = better match), 0 = no match
        """
        score = 0

        if self.system_contains:
            if self.system_contains.lower() in system.lower():
                score += 10
            else:
                return 0

        if self.message_contains:
            msg_text = " ".join(
                m.get("content", "") for m in messages if isinstance(m.get("content"), str)
            )
            if self.message_contains.lower() in msg_text.lower():
                score += 10
            else:
                return 0

        if self.agent_id_pattern:
            if re.search(self.agent_id_pattern, agent_id):
                score += 5
            else:
                return 0

        # Scenario match (lowest priority, used as fallback)
        if self.scenario and score == 0:
            score += 1

        return score if score > 0 else 1  # Return 1 for unfiltered responses

    def to_response(self) -> UnifiedResponse:
        """Convert to UnifiedResponse."""
        content = []

        if self.text:
            content.append(TextBlock(text=self.text))

        for tool_call in self.tool_calls:
            content.append(ToolUseBlock(
                id=tool_call.get("id", f"tool_{len(content)}"),
                name=tool_call.get("name", ""),
                input=tool_call.get("input", {})
            ))

        return UnifiedResponse(
            content=content,
            stop_reason=self.stop_reason if self.tool_calls else "end_turn",
            usage=Usage(
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
                cached_input_tokens=self.cached_input_tokens
            )
        )


class MockLLMClient:
    """Mock LLM client that returns pre-configured responses.

    Example:
        mock = MockLLMClient()
        mock.add_response(MockResponse(
            system_contains="planning",
            text="1. Analyze the task\n2. Execute steps"
        ))

        with mock.patch():
            result = planner.create_plan(job)
    """

    def __init__(self):
        self.responses: List[MockResponse] = []
        self.calls: List[RecordedCall] = []
        self.default_response: Optional[MockResponse] = None

        # Mimic UnifiedClient attributes
        self.provider_name = "mock"
        self.model_name = "mock-1.0"

    def add_response(self, response: MockResponse) -> "MockLLMClient":
        """Add a response configuration. Returns self for chaining."""
        self.responses.append(response)
        return self

    def set_default_response(self, response: MockResponse) -> "MockLLMClient":
        """Set a fallback response when no others match."""
        self.default_response = response
        return self

    def create(
        self,
        max_tokens: int,
        system: str,
        messages: list,
        tools: Optional[list] = None,
        agent_id: str = "unknown",
        job_id: Optional[str] = None,
        track_cost: bool = True,
        enabled_agent_count: int = 1,
    ) -> UnifiedResponse:
        """Mock implementation of UnifiedClient.create().

        Finds the best matching response and returns it.
        Records the call for test assertions.
        """
        # Find best matching response
        best_match = None
        best_score = 0

        for resp in self.responses:
            score = resp.matches(system, messages, agent_id)
            if score > best_score:
                best_score = score
                best_match = resp

        if best_match is None:
            if self.default_response:
                best_match = self.default_response
            else:
                # Return empty response if no match
                best_match = MockResponse(text="(no matching mock response)")

        response = best_match.to_response()

        # Record the call
        self.calls.append(RecordedCall(
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            tools=tools,
            agent_id=agent_id,
            job_id=job_id,
            response=response
        ))

        return response

    def get_calls(self, agent_id_pattern: str = None) -> List[RecordedCall]:
        """Get recorded calls, optionally filtered by agent_id pattern."""
        if agent_id_pattern:
            return [c for c in self.calls if re.search(agent_id_pattern, c.agent_id)]
        return self.calls

    def clear_calls(self):
        """Clear recorded call history."""
        self.calls = []

    @contextmanager
    def patch(self):
        """Context manager that patches get_client() to return this mock.

        Usage:
            mock = MockLLMClient()
            with mock.patch():
                # get_client() returns mock here
                result = agent.chat("hello")
        """
        with patch("src.llms.base.get_client", return_value=self):
            # Also patch the cached client to prevent real client creation
            with patch("src.llms.base._cached_client", self):
                yield self

    @classmethod
    def from_fixture(cls, fixture_name: str) -> "MockLLMClient":
        """Load a MockLLMClient from a JSON fixture file.

        Args:
            fixture_name: Name of fixture file (without .json extension)

        Returns:
            MockLLMClient configured with responses from the fixture
        """
        fixture_path = FIXTURES_DIR / f"{fixture_name}.json"

        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {fixture_path}")

        with open(fixture_path) as f:
            data = json.load(f)

        mock = cls()

        for resp_data in data.get("responses", []):
            mock.add_response(MockResponse(
                scenario=resp_data.get("scenario", ""),
                system_contains=resp_data.get("system_contains", ""),
                message_contains=resp_data.get("message_contains", ""),
                agent_id_pattern=resp_data.get("agent_id_pattern", ""),
                text=resp_data.get("text", ""),
                tool_calls=resp_data.get("tool_calls", []),
                stop_reason=resp_data.get("stop_reason", "end_turn"),
                input_tokens=resp_data.get("input_tokens", 100),
                output_tokens=resp_data.get("output_tokens", 50),
                cached_input_tokens=resp_data.get("cached_input_tokens", 0)
            ))

        if "default" in data:
            mock.set_default_response(MockResponse(
                text=data["default"].get("text", ""),
                tool_calls=data["default"].get("tool_calls", []),
                stop_reason=data["default"].get("stop_reason", "end_turn")
            ))

        return mock

    @classmethod
    def simple(cls, text: str = "", tool_calls: List[Dict] = None) -> "MockLLMClient":
        """Create a simple mock that returns the same response for all calls.

        Args:
            text: Text response to return
            tool_calls: Optional list of tool calls

        Returns:
            MockLLMClient that returns the specified response
        """
        mock = cls()
        mock.set_default_response(MockResponse(
            text=text,
            tool_calls=tool_calls or []
        ))
        return mock
