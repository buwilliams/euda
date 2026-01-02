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

    def _append_to_lifelog(self, user_message: str, assistant_response: str):
        """Append a conversation exchange to today's lifelog."""
        from .tools.user import write_lifelog

        # Format the conversation for the lifelog
        content = f"**Conversation with {self.config.get('name', self.id)}**\n\n"
        content += f"**User:** {user_message}\n\n"
        content += f"**{self.config.get('name', self.id)}:** {assistant_response}"

        write_lifelog(content)

    def _get_memory_path(self) -> Path:
        """Get path to agent memory file."""
        state_dir = AGENTS_DIR / self.id / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir / "memory.json"

    def _get_log_path(self) -> Path:
        """Get path to today's log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_dir = AGENTS_DIR / self.id / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / f"{today}.json"

    def _log(self, event: str, details: Optional[dict] = None):
        """Append a log entry to today's log file."""
        path = self._get_log_path()

        # Load existing logs or start fresh
        logs = []
        if path.exists():
            try:
                with open(path) as f:
                    logs = json.load(f)
            except (json.JSONDecodeError, IOError):
                logs = []

        # Append new entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
        }
        if details:
            entry["details"] = details
        logs.append(entry)

        # Save
        with open(path, "w") as f:
            json.dump(logs, f, indent=2)

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

    def _get_system_config(self) -> dict:
        """Load system configuration."""
        config_path = DATA_DIR / "system" / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {}

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
        self._log("chat_start", {"message_length": len(message)})
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
        self._log("llm_response", {
            "stop_reason": response.stop_reason,
            "usage": {"input": response.usage.input_tokens, "output": response.usage.output_tokens}
        })

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
            self._log("llm_response", {
                "stop_reason": response.stop_reason,
                "usage": {"input": response.usage.input_tokens, "output": response.usage.output_tokens}
            })

        # Extract text response
        text_response = ""
        for block in response.content:
            if hasattr(block, "text"):
                text_response += block.text

        self._save_conversation_turn("assistant", text_response)
        self._log("chat_end", {"response_length": len(text_response)})

        # Log conversations to lifelog for the friend agent (for Profiler to analyze)
        if self.id == "friend":
            self._append_to_lifelog(message, text_response)

        return text_response

    def _execute_tools(self, response) -> list:
        """Execute tool calls and return results."""
        from .tools import execute_tool
        from .tools.system import set_agent_context, clear_agent_context

        # Set agent context so tools can access this agent
        set_agent_context(self)

        results = []
        try:
            for block in response.content:
                if block.type == "tool_use":
                    self._log("tool_call", {"tool": block.name, "input": block.input})
                    result = execute_tool(block.name, block.input)
                    self._log("tool_result", {"tool": block.name, "success": not isinstance(result, dict) or "error" not in result})
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                    })
        finally:
            clear_agent_context()

        return results

    def work_cycle_sync(self):
        """Perform one cycle of autonomous work (synchronous version for threads)."""
        from .tools.jobs import list_jobs

        self._log("work_cycle_start")
        self._work_done = False

        # Get jobs that might need attention
        jobs = list_jobs(status="todo")

        if not jobs:
            self._log("work_cycle_end", {"reason": "no_jobs"})
            return  # Nothing to do

        self._log("work_cycle_jobs_found", {"count": len(jobs)})

        # Initial prompt asking agent to check for work
        prompt = f"""Check if any of these jobs need your attention based on your role:

Jobs:
{json.dumps(jobs, indent=2)}

Work on any jobs that match your role. When you're finished working (or if nothing matches your role), call the done_working tool to signal you're ready to sleep."""

        # Autonomous loop - keep working until agent calls done_working
        max_iterations = self._get_system_config().get("agents", {}).get("max_work_iterations", 20)
        iteration = 0

        while not self._work_done and iteration < max_iterations:
            iteration += 1
            self._log("work_iteration", {"iteration": iteration})

            response = self.chat(prompt)
            print(f"[{self.id}] {response[:100]}...")

            if self._work_done:
                break

            # Continue prompt for subsequent iterations
            prompt = "Continue working on your tasks. When finished, call done_working."

        if iteration >= max_iterations:
            self._log("work_cycle_end", {"reason": "max_iterations", "iterations": iteration})
        else:
            self._log("work_cycle_end", {"reason": "done_working", "iterations": iteration})

    async def work_cycle(self):
        """Perform one cycle of autonomous work (async wrapper)."""
        return self.work_cycle_sync()
