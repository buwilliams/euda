"""
Agent - Generic agent that runs based on configuration.

An agent is defined by:
1. Config (config.json) - operational parameters
2. Persona ({agent}-persona.md) - identity and behavior
3. Tools - list of tool names the agent can use
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic


DATA_DIR = Path(__file__).parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


class Agent:
    """A generic agent that operates based on its configuration."""

    def __init__(self, agent_id: str, config: Optional[dict] = None):
        self.id = agent_id
        self.config = config or self._load_config()
        self.persona = self._load_persona()
        self.client = anthropic.Anthropic()

    def _load_config(self) -> dict:
        """Load agent configuration from disk."""
        config_path = AGENTS_DIR / self.id / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {
            "id": self.id,
            "name": self.id.title(),
            "enabled": True,
            "tools": [],
            "sleep_minutes": 5
        }

    def _load_persona(self) -> str:
        """Load agent persona from disk."""
        persona_path = AGENTS_DIR / self.id / f"{self.id}-persona.md"
        if persona_path.exists():
            return persona_path.read_text()
        return f"You are {self.config.get('name', self.id)}, a helpful assistant."

    def _get_conversation_path(self) -> Path:
        """Get path to today's conversation file."""
        today = datetime.now().strftime("%Y-%m-%d")
        conv_dir = AGENTS_DIR / self.id / "state" / "conversation"
        conv_dir.mkdir(parents=True, exist_ok=True)
        return conv_dir / f"{today}.md"

    def _load_conversation_history(self) -> str:
        """Load today's conversation history."""
        path = self._get_conversation_path()
        if path.exists():
            return path.read_text()
        return ""

    def _save_conversation_turn(self, role: str, content: str):
        """Append a conversation turn to today's file."""
        path = self._get_conversation_path()
        timestamp = datetime.now().strftime("%H:%M:%S")

        with open(path, "a") as f:
            f.write(f"\n## {role.title()} ({timestamp})\n\n{content}\n")

    def _get_memory_path(self) -> Path:
        """Get path to agent memory file."""
        state_dir = AGENTS_DIR / self.id / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir / "memory.json"

    def _load_memory(self) -> dict:
        """Load agent's persistent memory."""
        path = self._get_memory_path()
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {}

    def _save_memory(self, memory: dict):
        """Save agent's persistent memory."""
        path = self._get_memory_path()
        with open(path, "w") as f:
            json.dump(memory, f, indent=2)

    def _build_system_prompt(self) -> str:
        """Build the system prompt from persona and context."""
        parts = [self.persona]

        # Add memory context if present
        memory = self._load_memory()
        if memory:
            parts.append("\n## Your Memory\n")
            for key, value in memory.items():
                parts.append(f"- {key}: {value}")

        # Add recent conversation context
        history = self._load_conversation_history()
        if history:
            # Include last portion of history to stay within context limits
            lines = history.split("\n")
            if len(lines) > 100:
                lines = lines[-100:]
            parts.append("\n## Recent Conversation\n")
            parts.append("\n".join(lines))

        return "\n".join(parts)

    def _get_tools(self) -> list:
        """Get tool definitions for this agent."""
        from .tools import get_tools_for_agent
        return get_tools_for_agent(self.config.get("tools", []))

    def chat(self, message: str) -> str:
        """Process a chat message and return response."""
        self._save_conversation_turn("user", message)

        tools = self._get_tools()
        system_prompt = self._build_system_prompt()

        messages = [{"role": "user", "content": message}]

        # Call Claude with tools
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            tools=tools if tools else None,
            messages=messages
        )

        # Handle tool use in a loop
        while response.stop_reason == "tool_use":
            tool_results = self._execute_tools(response)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_prompt,
                tools=tools if tools else None,
                messages=messages
            )

        # Extract text response
        text_response = ""
        for block in response.content:
            if hasattr(block, "text"):
                text_response += block.text

        self._save_conversation_turn("assistant", text_response)
        return text_response

    def _execute_tools(self, response) -> list:
        """Execute tool calls and return results."""
        from .tools import execute_tool

        results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                })

        return results

    async def work_cycle(self):
        """Perform one cycle of autonomous work."""
        from .tools.jobs import list_jobs

        # Get jobs that might need attention
        jobs = list_jobs(status="todo")

        if not jobs:
            return  # Nothing to do

        # Build a prompt asking the agent to check for work
        prompt = f"""Check if any of these jobs need your attention based on your role:

Jobs:
{json.dumps(jobs, indent=2)}

If you find work to do, use your tools to complete it. If nothing matches your role, just say so briefly."""

        # Process through chat (which handles tools)
        response = self.chat(prompt)
        print(f"[{self.id}] {response[:100]}...")
