"""
LLM Mock Infrastructure

Provides MockLLMClient for testing LLM-dependent code paths without
making real API calls. Includes recording utilities to capture real
LLM responses for realistic test fixtures.

Usage:
    from tests.fixtures.llm import MockLLMClient

    # Use mock in tests
    mock_client = MockLLMClient.from_fixture("planning")
    with mock_client.patch():
        # Code that uses get_client() will get the mock
        result = planner.create_plan(topic)

    # For recording (imports real LLM client, run as script):
    # python -m tests.fixtures.llm.recorder --all
"""

from .mock_client import MockLLMClient, MockResponse

__all__ = ["MockLLMClient", "MockResponse"]
