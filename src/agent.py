"""
Agent - Generic agent that runs based on configuration.

An agent is defined by:
1. Config (config.json) - operational parameters
2. Persona ({agent}-persona.md) - identity and behavior
3. Tools - list of tool names the agent can use
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .llms import get_client


DATA_DIR = Path(__file__).parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


class Agent:
    """A generic agent that operates based on its configuration."""

    def __init__(self, agent_id: str, config: Optional[dict] = None, session_id: Optional[str] = None):
        self.id = agent_id
        self.config = config or self._load_config()
        self.persona = self._load_persona()
        self._work_done = False
        self._session_id = session_id
        self._current_job_id = None

    def wait_for_trigger(self, timeout: float = None) -> Optional[dict]:
        """Wait for a trigger event from the event bus.

        Args:
            timeout: Maximum seconds to wait (None = wait forever)

        Returns:
            Event dict with keys: event, data, timestamp
            None if timeout or not subscribed
        """
        from .events import get_event_bus
        bus = get_event_bus()
        if not bus:
            return None
        return bus.wait_for_event(self.id, timeout=timeout)

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
            "triggers": ["job:assigned"]
        }

    def _load_persona(self) -> str:
        """Load agent persona from disk."""
        persona_path = AGENTS_DIR / self.id / f"{self.id}-persona.md"
        if persona_path.exists():
            return persona_path.read_text()
        return f"You are {self.config.get('name', self.id)}, a helpful assistant."

    def _get_conversation_dir(self) -> Path:
        """Get conversation directory for this agent."""
        conv_dir = AGENTS_DIR / self.id / "state" / "conversation"
        conv_dir.mkdir(parents=True, exist_ok=True)
        return conv_dir

    def _get_conversation_path(self) -> Path:
        """Get path to current session's conversation file."""
        conv_dir = self._get_conversation_dir()
        # Create session ID if not set
        if not self._session_id:
            self._session_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        return conv_dir / f"{self._session_id}.md"

    def set_session(self, session_id: str):
        """Set the current session ID."""
        self._session_id = session_id

    def get_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._session_id

    def set_job_context(self, job_id: str):
        """Set the current job context for the agent."""
        self._current_job_id = job_id

    def clear_job_context(self):
        """Clear the current job context."""
        self._current_job_id = None

    def _get_job_context_for_prompt(self) -> str:
        """Build job context string for system prompt."""
        if not self._current_job_id:
            return ""

        from .tools.jobs import get_job
        from .tools.assets import list_assets, read_asset

        job = get_job(self._current_job_id)
        if not job:
            return ""

        parts = ["## Current Job Context\n"]
        parts.append(f"**Job:** {job.get('name', 'Untitled')}")

        if job.get('description'):
            parts.append(f"\n**Description:** {job['description']}")

        if job.get('due_date'):
            parts.append(f"\n**Due:** {job['due_date']}")

        # Get text-based assets
        assets = list_assets(self._current_job_id)
        text_assets = []
        for asset in assets:
            mime = asset.get('mime_type', '')
            if mime and (mime.startswith('text/') or mime in ['application/json', 'application/xml']):
                text_assets.append(asset)

        if text_assets:
            parts.append("\n\n### Attached Files\n")
            for asset in text_assets:
                content = read_asset(self._current_job_id, asset['filename'])
                if content and 'content' in content:
                    parts.append(f"\n**{asset['filename']}:**\n```\n{content['content']}\n```")

        return "\n".join(parts)

    def _load_conversation_history(self) -> str:
        """Load current session's conversation history."""
        path = self._get_conversation_path()
        if path.exists():
            return path.read_text()
        return ""

    def _save_conversation_turn(self, role: str, content: str):
        """Append a conversation turn to session file."""
        path = self._get_conversation_path()
        timestamp = datetime.now().strftime("%H:%M:%S")

        with open(path, "a") as f:
            f.write(f"\n## {role.title()} ({timestamp})\n\n{content}\n")

    def _append_to_lifelog(self, user_message: str, assistant_response: str):
        """Append a conversation exchange to today's lifelog."""
        from .tools.user import write_lifelog

        agent_name = self.config.get('name', self.id)

        # Format the conversation for the lifelog
        content = f"**User:** {user_message}\n\n"
        content += f"**{agent_name}:** {assistant_response}"

        write_lifelog(content, agent=agent_name)

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
        from .tools.user import get_user_profile
        from .tools.top_of_mind import get_top_of_mind_for_prompt

        parts = [self.persona]

        # Add user profile for context about who we're serving
        profile = get_user_profile()
        if profile.get("exists") and profile.get("content"):
            parts.append("\n## User Profile\n")
            parts.append(profile["content"])

        # Add top-of-mind items for context about what user is focused on
        top_of_mind = get_top_of_mind_for_prompt()
        if top_of_mind:
            parts.append("\n" + top_of_mind)

        # Add current job context if working on a specific job
        job_context = self._get_job_context_for_prompt()
        if job_context:
            parts.append("\n" + job_context)

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

    def chat(self, message: str, log_to_lifelog: bool = True, save_to_history: bool = True) -> str:
        """Process a chat message and return response.

        Args:
            message: The user message
            log_to_lifelog: Whether to log this conversation to lifelog (default True)
            save_to_history: Whether to save to conversation history (default True)
        """
        self._log("chat_start", {"message_length": len(message)})
        if save_to_history:
            self._save_conversation_turn("user", message)

        tools = self._get_tools()
        system_prompt = self._build_system_prompt()

        messages = [{"role": "user", "content": message}]

        # Get fresh client (respects current provider config)
        # Client handles budget checking, cost tracking, and rate limiting automatically
        client = get_client()

        # Call LLM with tools
        response = client.create(
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            tools=tools if tools else None,
            agent_id=self.id
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

            response = client.create(
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=tools if tools else None,
                agent_id=self.id
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

        if save_to_history:
            self._save_conversation_turn("assistant", text_response)
        self._log("chat_end", {"response_length": len(text_response)})

        # Log user conversations to lifelog for the friend agent (for Profiler to analyze)
        # Only log actual user conversations, not autonomous work cycles
        if self.id == "friend" and log_to_lifelog:
            self._append_to_lifelog(message, text_response)

        return text_response

    def _execute_tools(self, response) -> list:
        """Execute tool calls and return results."""
        from .tools import execute_tool
        from .tools.system import set_agent_context, clear_agent_context
        from .tool_batcher import execute_tools_batched

        # Set agent context so tools can access this agent
        set_agent_context(self)

        try:
            # Collect all tool calls
            tool_calls = [block for block in response.content if block.type == "tool_use"]

            # Log individual calls for debugging
            for block in tool_calls:
                self._log("tool_call", {"tool": block.name, "input": block.input})

            # Execute with automatic batching
            results = execute_tools_batched(tool_calls, execute_tool, agent_id=self.id)

            # Log results
            for block, result in zip(tool_calls, results):
                self._log("tool_result", {"tool": block.name, "success": "error" not in result.get("content", "")})

            return results
        finally:
            clear_agent_context()

    def work_cycle_sync(self, trigger_context: dict = None):
        """Perform one cycle of autonomous work (synchronous version for threads).

        Args:
            trigger_context: Optional event data that triggered this cycle
        """
        from .tools.jobs import list_jobs

        self._log("work_cycle_start", {"trigger": trigger_context})
        self._work_done = False

        # Get jobs that might need attention
        jobs = list_jobs(status="todo")

        # Build trigger info for the prompt
        trigger_info = ""
        if trigger_context:
            trigger_info = f"\n\nYou were triggered by event: {trigger_context.get('event')}"
            if trigger_context.get('data'):
                trigger_info += f"\nEvent data: {json.dumps(trigger_context['data'])}"

        if not jobs:
            self._log("work_cycle_end", {"reason": "no_jobs"})
            return  # Nothing to do

        self._log("work_cycle_jobs_found", {"count": len(jobs)})

        # Initial prompt asking agent to check for work
        prompt = f"""Check if any of these jobs need your attention based on your role:{trigger_info}

Jobs:
{json.dumps(jobs, indent=2)}

Work on any jobs that match your role. When you're finished working (or if nothing matches your role), call the done_working tool to signal you're done."""

        # Autonomous loop - keep working until agent calls done_working
        max_iterations = self._get_system_config().get("agents", {}).get("max_work_iterations", 20)
        iteration = 0

        while not self._work_done and iteration < max_iterations:
            iteration += 1
            self._log("work_iteration", {"iteration": iteration})

            # Don't log autonomous work cycles to lifelog or history - only user conversations
            response = self.chat(prompt, log_to_lifelog=False, save_to_history=False)
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
