"""
LLMResponseRecorder - Record real LLM responses for test fixtures.

Captures actual LLM responses to create realistic test fixtures.
Run this when you need to update fixtures with current LLM behavior.

Usage:
    python -m tests.fixtures.llm.recorder --scenario planning
    python -m tests.fixtures.llm.recorder --all
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.llms.base import get_client, UnifiedResponse


FIXTURES_DIR = Path(__file__).parent / "responses"


class LLMResponseRecorder:
    """Record real LLM responses for creating test fixtures.

    Captures actual API responses along with the prompts that generated them,
    allowing tests to use realistic responses.
    """

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or FIXTURES_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.recordings: List[Dict] = []

    def record(
        self,
        scenario: str,
        system: str,
        messages: list,
        max_tokens: int = 500,
        tools: list = None,
        agent_id: str = "recorder",
        description: str = ""
    ) -> Dict:
        """Record a real LLM response.

        Args:
            scenario: Name for this recording (used for matching)
            system: System prompt
            messages: Conversation messages
            max_tokens: Max tokens for response
            tools: Optional tool definitions
            agent_id: Agent ID for the call
            description: Human-readable description

        Returns:
            Dict with request/response data
        """
        client = get_client()

        print(f"Recording scenario: {scenario}")
        print(f"  System prompt: {system[:100]}...")

        response = client.create(
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            tools=tools,
            agent_id=agent_id,
            track_cost=True
        )

        # Convert response to serializable format
        response_data = self._serialize_response(response)

        recording = {
            "scenario": scenario,
            "description": description,
            "recorded_at": datetime.now().isoformat(),
            "request": {
                "system": system,
                "messages": messages,
                "max_tokens": max_tokens,
                "tools": [t.get("name") for t in tools] if tools else None,
                "agent_id": agent_id
            },
            "response": response_data
        }

        self.recordings.append(recording)

        print(f"  Response: {response_data.get('text', '')[:100]}...")
        print(f"  Tokens: {response.usage.input_tokens} in, {response.usage.output_tokens} out")

        return recording

    def _serialize_response(self, response: UnifiedResponse) -> Dict:
        """Convert UnifiedResponse to serializable dict."""
        text = ""
        tool_calls = []

        for block in response.content:
            if hasattr(block, "text"):
                text += block.text
            elif hasattr(block, "name"):
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })

        return {
            "text": text,
            "tool_calls": tool_calls,
            "stop_reason": response.stop_reason,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cached_input_tokens": response.usage.cached_input_tokens
        }

    def save_fixture(self, name: str, include_requests: bool = False):
        """Save recordings to a fixture file.

        Args:
            name: Fixture filename (without .json)
            include_requests: Whether to include full request data
        """
        fixture_path = self.output_dir / f"{name}.json"

        # Convert recordings to fixture format
        responses = []
        for rec in self.recordings:
            resp = {
                "scenario": rec["scenario"],
                "text": rec["response"]["text"],
                "tool_calls": rec["response"]["tool_calls"],
                "stop_reason": rec["response"]["stop_reason"],
                "input_tokens": rec["response"]["input_tokens"],
                "output_tokens": rec["response"]["output_tokens"]
            }

            # Add matching hints based on request
            if rec["request"]["system"]:
                # Extract a distinctive phrase from system prompt
                system_words = rec["request"]["system"].split()[:10]
                resp["system_contains"] = " ".join(system_words[:5])

            if rec["request"]["agent_id"]:
                resp["agent_id_pattern"] = rec["request"]["agent_id"].replace("/", "\\/")

            responses.append(resp)

        fixture_data = {
            "name": name,
            "generated_at": datetime.now().isoformat(),
            "responses": responses
        }

        if include_requests:
            fixture_data["_recordings"] = self.recordings

        with open(fixture_path, "w") as f:
            json.dump(fixture_data, f, indent=2)

        print(f"Saved fixture: {fixture_path}")

    def clear(self):
        """Clear recorded responses."""
        self.recordings = []


# ============== Pre-defined Scenarios ==============

def record_planning_scenarios(recorder: LLMResponseRecorder):
    """Record planning-related LLM responses."""
    from src.agent.cognition.reasoning.planning import (
        PLANNING_SYSTEM_PROMPT, PLANNING_USER_PROMPT
    )

    # Scenario: Simple topic planning
    recorder.record(
        scenario="planning_simple",
        description="Planning for a simple topic",
        system=PLANNING_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": PLANNING_USER_PROMPT.format(
                task_description="**Task:** Send daily summary email\n**Details:** Compile and send summary",
                available_tools="- **send_email**: Send an email\n- **list_topics**: List topics"
            )
        }]
    )

    # Scenario: Complex topic with multiple tools
    recorder.record(
        scenario="planning_complex",
        description="Planning for a complex multi-step topic",
        system=PLANNING_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": PLANNING_USER_PROMPT.format(
                task_description="**Task:** Research and summarize topic\n**Details:** Find information, analyze, create summary",
                available_tools="- **web_search**: Search the web\n- **read_file**: Read files\n- **write_file**: Write files\n- **create_topic**: Create sub-topics"
            )
        }]
    )


def record_append_scenarios(recorder: LLMResponseRecorder):
    """Record consolidation append phase responses."""
    from plugins.core.system.consolidation.prompts import (
        get_append_system_prompt, build_append_prompt
    )

    # Simple conversation extraction
    recorder.record(
        scenario="append_simple",
        description="Extract memories from simple conversation",
        system=get_append_system_prompt(),
        messages=[{
            "role": "user",
            "content": build_append_prompt(
                agent_identity="A helpful assistant focused on productivity.",
                existing_memory=[],
                user_message="I have a meeting with Sarah tomorrow at 3pm about the project deadline.",
                assistant_response="I'll help you remember that. Your meeting with Sarah is scheduled for tomorrow at 3pm to discuss the project deadline."
            )
        }],
        agent_id="user/reflection"
    )

    # Conversation with existing memory
    recorder.record(
        scenario="append_with_memory",
        description="Extract memories when memory already exists",
        system=get_append_system_prompt(),
        messages=[{
            "role": "user",
            "content": build_append_prompt(
                agent_identity="A helpful assistant focused on productivity.",
                existing_memory=[
                    {"type": "person", "short_description": "Sarah - project manager"},
                    {"type": "goal", "short_description": "Complete quarterly report"}
                ],
                user_message="The quarterly report is due next Friday. Also, I'm worried about the budget.",
                assistant_response="I've noted that the quarterly report deadline is next Friday. Regarding your budget concerns, would you like to discuss specific areas?"
            )
        }],
        agent_id="user/reflection"
    )

    # No new memories needed
    recorder.record(
        scenario="append_empty",
        description="Conversation with no noteworthy items",
        system=get_append_system_prompt(),
        messages=[{
            "role": "user",
            "content": build_append_prompt(
                agent_identity="A helpful assistant.",
                existing_memory=[],
                user_message="Hello!",
                assistant_response="Hello! How can I help you today?"
            )
        }],
        agent_id="user/reflection"
    )


def record_chat_scenarios(recorder: LLMResponseRecorder):
    """Record agent chat responses."""

    # Simple greeting
    recorder.record(
        scenario="chat_greeting",
        description="Simple greeting response",
        system="You are a helpful assistant named Chat. Be concise and friendly.",
        messages=[{"role": "user", "content": "Hello, how are you?"}],
        agent_id="user"
    )

    # Question requiring thought
    recorder.record(
        scenario="chat_question",
        description="Response to a general question",
        system="You are a helpful assistant named Chat. Be concise and friendly.",
        messages=[{"role": "user", "content": "What are three good habits for productivity?"}],
        agent_id="user"
    )


def record_all_scenarios():
    """Record all pre-defined scenarios."""
    recorder = LLMResponseRecorder()

    print("=" * 60)
    print("Recording LLM responses for test fixtures")
    print("=" * 60)
    print()

    print("--- Planning Scenarios ---")
    record_planning_scenarios(recorder)
    recorder.save_fixture("planning")
    recorder.clear()

    print()
    print("--- Append Scenarios ---")
    record_append_scenarios(recorder)
    recorder.save_fixture("append")
    recorder.clear()

    print()
    print("--- Chat Scenarios ---")
    record_chat_scenarios(recorder)
    recorder.save_fixture("chat")
    recorder.clear()

    print()
    print("=" * 60)
    print("All scenarios recorded successfully!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Record LLM responses for test fixtures")
    parser.add_argument(
        "--scenario",
        choices=["planning", "append", "chat", "all"],
        default="all",
        help="Which scenarios to record"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=FIXTURES_DIR,
        help="Output directory for fixtures"
    )

    args = parser.parse_args()

    recorder = LLMResponseRecorder(args.output_dir)

    if args.scenario == "all":
        record_all_scenarios()
    elif args.scenario == "planning":
        record_planning_scenarios(recorder)
        recorder.save_fixture("planning")
    elif args.scenario == "append":
        record_append_scenarios(recorder)
        recorder.save_fixture("append")
    elif args.scenario == "chat":
        record_chat_scenarios(recorder)
        recorder.save_fixture("chat")


if __name__ == "__main__":
    main()
