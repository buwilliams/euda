"""
Agent - Generic agent that runs based on configuration.

An agent follows the four-category ontology:
1. Identity (identity.md) - Purpose, values, voice, stable attractors
2. Cognition - Reasoning (prompts) + Metacognition (self-regulation)
3. Memory - Short-term (90 days) + Long-term (permanent archive)
4. Behavior (config.json) - Tools + Triggers + Modes
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from ..llms import get_client
from .logger import get_logger
from .cognition.metacognition import Metacognition, AgentState, Consolidation


DATA_DIR = Path(__file__).parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


class Agent:
    """A generic agent that operates based on its configuration."""

    def __init__(
        self,
        agent_id: str,
        config: Optional[dict] = None,
        session_id: Optional[str] = None,
        event_sink: Optional[Callable[[str, dict], None]] = None
    ):
        self.id = agent_id
        self.config = config or self._load_config()
        self.identity = self._load_identity()
        self._work_done = False
        self._session_id = session_id
        self._current_job_id = None
        self._event_sink = event_sink

        # Initialize consolidation (self-improvement) if enabled
        consolidation_config = self.config.get("consolidation", {})
        consolidation_enabled = consolidation_config.get("enabled", True)
        self.consolidation = Consolidation(self) if consolidation_enabled else None

        # Initialize metacognition (always created - inherent to all agents)
        self.metacognition = Metacognition(self)

    @property
    def state(self) -> AgentState:
        """Get the current operational state of this agent."""
        return self.metacognition.get_agent_state()

    def is_enabled(self) -> bool:
        """Check if this agent is enabled and can run."""
        return self.state == AgentState.ENABLED

    def wait_for_trigger(self, timeout: float = None) -> Optional[dict]:
        """Wait for a trigger event from the event bus.

        Args:
            timeout: Maximum seconds to wait (None = wait forever)

        Returns:
            Event dict with keys: event, data, timestamp
            None if timeout or not subscribed
        """
        from ..web.events import get_event_bus
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
            "state": "enabled",
            "tools": [],
            "triggers": ["job:assigned"]
        }

    def _load_identity(self) -> str:
        """Load agent identity from disk."""
        identity_path = AGENTS_DIR / self.id / "identity.md"
        if identity_path.exists():
            return identity_path.read_text()
        # Create from template if available
        template_path = AGENTS_DIR / self.id / "identity.template.md"
        if template_path.exists():
            identity_content = template_path.read_text()
            identity_path.write_text(identity_content)
            return identity_content
        return f"You are {self.config.get('name', self.id)}, a helpful assistant."

    def _get_user_identity(self) -> str:
        """Load the user's identity for context.

        All agents serve the user, so they need to know who the user is.
        This returns the user's identity.md content, which contains their
        purpose, values, interests, biographical info, etc.
        """
        # Don't include user identity for the user agent itself
        if self.id == "user":
            return "(You are the user.)"

        user_identity_path = AGENTS_DIR / "user" / "identity.md"
        if user_identity_path.exists():
            return user_identity_path.read_text()
        return "(User identity not yet established. Learn about them through conversation.)"

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

        from ..tools.data.jobs import get_job
        from ..tools.data.assets import list_assets, read_asset

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

    def _parse_conversation_history(self) -> list:
        """Parse conversation history markdown into message objects.

        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        import re

        history_text = self._load_conversation_history()
        if not history_text:
            return []

        messages = []
        # Parse markdown format: ## User (HH:MM:SS) or ## Assistant (HH:MM:SS)
        parts = re.split(r'^## (User|Assistant) \([^)]+\)\n\n', history_text, flags=re.MULTILINE)

        # parts[0] is empty or content before first header
        # parts[1] is role (User/Assistant), parts[2] is content
        # parts[3] is role, parts[4] is content, etc.
        i = 1
        while i < len(parts) - 1:
            role = parts[i].lower()
            msg_content = parts[i + 1].strip()
            if msg_content:
                messages.append({"role": role, "content": msg_content})
            i += 2

        return messages

    def _save_conversation_turn(self, role: str, content: str):
        """Append a conversation turn to session file."""
        path = self._get_conversation_path()
        timestamp = datetime.now().strftime("%H:%M:%S")

        with open(path, "a") as f:
            f.write(f"\n## {role.title()} ({timestamp})\n\n{content}\n")

    def _append_to_long_term_memory(self, user_message: str, assistant_response: str):
        """Append a conversation exchange to today's long-term memory."""
        from ..tools.data.memory import write_long_term_memory

        agent_name = self.config.get('name', self.id)

        # Format the conversation for long-term memory
        content = f"**User:** {user_message}\n\n"
        content += f"**{agent_name}:** {assistant_response}"

        write_long_term_memory(content, agent_id="user", source=agent_name)

    def _get_logger(self):
        """Get logger for this agent."""
        return get_logger(f"agents/{self.id}/logs")

    def _log(self, event: str, details: Optional[dict] = None):
        """Append a log entry to today's log file and optionally stream to sink."""
        entry = {"event": event}
        if details:
            entry["details"] = details
        self._get_logger().info(entry)

        # Stream to event sink if configured (for dev CLI)
        if self._event_sink:
            self._event_sink(event, {
                "agent_id": self.id,
                **(details or {})
            })

    def _get_system_config(self) -> dict:
        """Load system configuration."""
        config_path = DATA_DIR / "system" / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {}

    def _build_system_prompt(self, voice_input: bool = False) -> str:
        """Build the system prompt from identity, user context, and tools.

        Includes:
        - Agent's identity (from identity.md)
        - User's identity (so agents know who they serve)
        - Available tools grouped by type

        Note: User memory is NOT auto-injected (use list_memory tool for specifics).

        Args:
            voice_input: Whether input came from voice (enables conversational response style)
        """
        from ..tools import get_tools_grouped_by_type
        from .cognition.reasoning.prompts import render_template

        # Build tools section grouped by type
        tools_by_type = get_tools_grouped_by_type(self.config.get("tools", []))
        type_labels = {
            "data": "Data Tools",
            "agents": "Agent Tools",
            "system": "System Tools",
            "integration": "Integration Tools"
        }

        tools_sections = []
        for tool_type in ["data", "agents", "system", "integration"]:
            tools = tools_by_type.get(tool_type, [])
            if tools:
                tools_sections.append(f"### {type_labels[tool_type]}\n")
                for t in tools:
                    tools_sections.append(f"- **{t['name']}**: {t['description']}")
        tools_text = "\n".join(tools_sections) if tools_sections else "No tools available."

        # Load user identity so agents know who they serve
        user_identity = self._get_user_identity()

        prompt = render_template(
            "agent/system",
            identity=self.identity,
            user_identity=user_identity,
            tools_by_type=tools_text
        )

        # Voice mode instructions
        if voice_input:
            prompt += "\n\n## Voice Response Mode\n"
            prompt += (
                "The user is speaking to you via voice. Your response will be read aloud. "
                "Respond in natural, conversational first-person speech with complete sentences. "
                "Avoid bullet points, lists, job IDs, or formatted text. "
                "Speak as if you're talking directly to the user."
            )

        return prompt

    def _get_tools(self) -> list:
        """Get tool definitions for this agent."""
        from ..tools import get_tools_for_agent
        return get_tools_for_agent(self.config.get("tools", []))

    def _is_reflection_trigger(self, job_tags: list, job_name: str) -> bool:
        """Check if a job is a reflection trigger that should be handled directly.

        Consolidation jobs are identified by name pattern: Trigger:consolidation:{phase}:{date}
        """
        return job_name.startswith("Trigger:consolidation:")

    def _execute_reflection_trigger(self, job: dict):
        """Execute a reflection trigger directly (not through chat loop).

        This is more efficient than letting the agent chat loop handle reflection,
        as it makes a single LLM call instead of many.
        """
        from ..tools.data.jobs import complete_job

        job_id = job.get("id")
        job_tags = job.get("tags", [])

        # Extract execution_id from tags if present
        execution_id = None
        for tag in job_tags:
            if tag.startswith("execution:"):
                execution_id = tag.split(":", 1)[1]
                break

        # Determine phase from job name: Trigger:consolidation:{phase}:{date}
        job_name = job.get("name", "")
        phase = "both"  # default
        if job_name.startswith("Trigger:consolidation:"):
            parts = job_name.split(":")
            if len(parts) >= 3:
                phase = parts[2]  # Trigger:consolidation:{phase}:{date}

        self._log("reflection_trigger_start", {
            "job_id": job_id,
            "phase": phase,
            "execution_id": execution_id
        })

        try:
            if self.consolidation:
                if phase in ("append", "both"):
                    # Append is usually done automatically after chat, skip for manual triggers
                    pass
                if phase in ("consolidate", "both"):
                    self.consolidation.consolidate(execution_id=execution_id)

            # Complete the trigger job
            complete_job(job_id)

            self._log("reflection_trigger_complete", {
                "job_id": job_id,
                "phase": phase,
                "execution_id": execution_id
            })

        except Exception as e:
            self._log("reflection_trigger_error", {
                "job_id": job_id,
                "phase": phase,
                "error": str(e)
            })
            # Don't re-raise - let manager handle retries if needed

    def _get_job_prompt_type(self, job: dict) -> str:
        """Determine which prompt template to use based on job type.

        Returns:
            Template name: 'agent/consolidation' or 'agent/job_assignment'
        """
        job_name = job.get("name", "")

        # Consolidation jobs identified by name pattern: Trigger:consolidation:{phase}:{date}
        # Note: these are now handled directly in _execute_reflection_trigger
        # This path is kept for backwards compatibility with any code that calls this directly
        if job_name.startswith("Trigger:consolidation:"):
            return "agent/consolidation"
        # Regular job assignment (includes user:request)
        else:
            return "agent/job_assignment"

    def _format_job_prompt(self, job: dict, remaining: int = 0) -> str:
        """Format a job as a standardized prompt for the agent."""
        from ..tools.data.assets import list_assets
        from ..tools.data.memory import get_memory_for_prompt
        from .cognition.reasoning.prompts import render_template

        assets = list_assets(job['id'])
        if assets:
            names = [a['filename'] for a in assets]
            attachments = f"{len(assets)} attachment(s): {', '.join(names)}"
        else:
            attachments = "No attachments"

        remaining_notice = f"({remaining} more jobs waiting)" if remaining > 0 else ""

        tags = job.get('tags', [])
        tags_str = ', '.join(tags) if tags else 'None'

        # Select prompt template based on job type
        template_name = self._get_job_prompt_type(job)

        return render_template(
            template_name,
            agent_id=self.id,  # For agent-specific template lookup
            job_id=job.get('id'),
            job_name=job.get('name', 'Untitled'),
            job_description=job.get('description') or 'None provided',
            job_due_date=job.get('due_date') or 'No deadline',
            job_tags=tags_str,
            job_attachments=attachments,
            remaining_jobs_notice=remaining_notice
        )

    def chat(self, message: str, log_to_memory: bool = True, save_to_history: bool = True,
             voice_input: bool = False, defer_consolidation: bool = False) -> str:
        """Process a chat message and return response.

        Args:
            message: The user message
            log_to_memory: Whether to log this conversation to long-term memory (default True)
            save_to_history: Whether to save to conversation history (default True)
            voice_input: Whether input came from voice (enables conversational response style)
            defer_consolidation: If True, skip reflection append (caller will batch it)
        """
        self._log("chat_start", {"message_length": len(message)})

        tools = self._get_tools()
        system_prompt = self._build_system_prompt(voice_input=voice_input)

        # Load conversation history and append current message
        messages = self._parse_conversation_history()
        messages.append({"role": "user", "content": message})

        # Save user message to history after parsing (to avoid duplicates)
        if save_to_history:
            self._save_conversation_turn("user", message)

        # Get fresh client (respects current provider config)
        # Client handles budget checking, cost tracking, and rate limiting automatically
        client = get_client()

        # Get max_output_tokens from current provider config (default 16000)
        config = self._get_system_config()
        llm_config = config.get("llm", {})
        provider = llm_config.get("provider", "openai")
        provider_config = llm_config.get("providers", {}).get(provider, {})
        max_tokens = provider_config.get("max_output_tokens", 16000)

        # Call LLM with tools
        response = client.create(
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
            tools=tools if tools else None,
            agent_id=self.id,
            job_id=self._current_job_id
        )

        self._log("llm_response", {
            "stop_reason": response.stop_reason,
            "usage": {"input": response.usage.input_tokens, "output": response.usage.output_tokens}
        })

        # Handle tool use in a loop
        self.metacognition.reset_iteration()

        while response.stop_reason == "tool_use":
            tool_results = self._execute_tools(response)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = client.create(
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
                tools=tools if tools else None,
                agent_id=self.id,
                job_id=self._current_job_id
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

        # Log user conversations to long-term memory for the chat agent
        # Only log actual user conversations, not autonomous work cycles
        if self.id == "chat" and log_to_memory:
            self._append_to_long_term_memory(message, text_response)

        # Run reflection append phase to extract noteworthy items
        # Skip if defer_consolidation=True (caller will batch process)
        if self.consolidation and log_to_memory and not defer_consolidation:
            self.consolidation.append(message, text_response)

        return text_response

    def _execute_tools(self, response) -> list:
        """Execute tool calls and return results."""
        import json
        from ..tools import execute_tool
        from ..tools.system.system import set_agent_context, clear_agent_context

        # Set agent context so tools can access this agent
        set_agent_context(self)

        try:
            # Collect all tool calls
            tool_calls = [block for block in response.content if block.type == "tool_use"]
            results = []

            # Execute each tool call
            for block in tool_calls:
                self._log("tool_call", {"tool": block.name, "input": block.input})
                # Record for action/progress awareness
                self.metacognition.record_tool_call(block.name, block.input)

                # Execute tool
                result = execute_tool(block.name, block.input)

                # Format result for LLM
                formatted = {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                }
                results.append(formatted)

                # Log result
                self._log("tool_result", {"tool": block.name, "success": "error" not in formatted.get("content", "")})

            return results
        finally:
            clear_agent_context()

    def work_cycle_sync(self, trigger_context: dict = None):
        """Perform one cycle of autonomous work (synchronous version for threads).

        The agent discovers, claims, works, and releases jobs autonomously.
        The manager only starts agents and monitors health.

        Args:
            trigger_context: Optional event data that triggered this cycle
        """
        from ..tools.data.jobs import list_jobs, claim_job, release_job

        self._log("work_cycle_start", {"trigger": trigger_context})
        self._work_done = False
        self.metacognition.reset_work_cycle()  # Reset tracking for new work cycle

        # Query for actionable todo jobs assigned to this agent
        jobs = list_jobs(status="todo", assignee=self.id, actionable=True)
        if not jobs:
            self._log("work_cycle_end", {"reason": "no_jobs"})
            return  # Nothing to do

        self._log("work_cycle_jobs_found", {"count": len(jobs)})

        # Work the first job - after completion, manager will trigger another cycle if more exist
        current_job = jobs[0]
        remaining = len(jobs) - 1
        job_id = current_job.get("id")

        # Claim the job exclusively (sets status to 'working')
        claim_result = claim_job(job_id, self.id)
        if "error" in claim_result:
            self._log("job_claim_failed", {"job_id": job_id, "error": claim_result.get("error")})
            return  # Job was claimed by another agent

        self._log("job_claimed", {"job_id": job_id})

        # Set job context for cost/rate tracking
        self._current_job_id = job_id

        try:
            # Special handling for reflection triggers - call reflection directly instead of chat loop
            # This is much more efficient (single LLM call vs many)
            job_tags = current_job.get("tags", [])
            job_name = current_job.get("name", "")
            if self._is_reflection_trigger(job_tags, job_name):
                self._execute_reflection_trigger(current_job)
                return

            # Use standardized job prompt format
            from .cognition.reasoning.prompts import load_template
            prompt = self._format_job_prompt(current_job, remaining)

            # Strategic planning phase (if configured for this job type)
            plan = None
            if self.metacognition.planner.should_plan(current_job):
                self._log("planning_start", {"job_id": current_job.get("id")})
                plan = self.metacognition.planner.create_plan(current_job)
                if plan:
                    prompt = self.metacognition.planner.inject_plan(prompt, plan)
                    self._log("planning_injected", {"job_id": current_job.get("id"), "plan_length": len(plan)})

            # Autonomous loop - keep working until agent calls done_working
            iteration = 0

            # Check if deferred reflection is enabled (efficiency optimization)
            defer_consolidation = self.metacognition.should_defer_consolidation()
            exchanges = []  # Collect for batched reflection if deferred

            try:
                while not self._work_done:
                    iteration += 1
                    self._log("work_iteration", {"iteration": iteration})

                    # Check for stuck patterns before proceeding
                    stuck_reason = self.metacognition.check_stuck()
                    if stuck_reason:
                        self._log("stuck_detected", {"reason": stuck_reason, "iteration": iteration})
                        print(f"[{self.id}] Stuck detected: {stuck_reason}")
                        # Don't break immediately - let the agent know it's stuck via the continue prompt
                        break

                    # Log to memory for memory creation, but don't save to conversation history
                    # Defer reflection if enabled (will batch process at end)
                    response = self.chat(prompt, log_to_memory=True, save_to_history=False,
                                         defer_consolidation=defer_consolidation)

                    # Collect exchange for batched reflection
                    if defer_consolidation and self.consolidation:
                        exchanges.append((prompt, response))

                    print(f"[{self.id}] {response[:100]}...")

                    if self._work_done:
                        break

                    # Continue prompt for subsequent iterations with progress context
                    progress_ctx = self.metacognition.get_progress_context()

                    # Format stuck warning if detected
                    stuck_warning = ""
                    if progress_ctx.get("stuck_warning"):
                        stuck_warning = f"**Warning:** {progress_ctx['stuck_warning']}"

                    prompt = load_template("agent/continue_with_context").format(
                        iteration=progress_ctx.get("iteration", iteration),
                        tool_calls_this_cycle=progress_ctx.get("tool_calls_this_cycle", 0),
                        stuck_warning=stuck_warning
                    )

                self._log("work_cycle_end", {"reason": "done_working", "iterations": iteration})
            finally:
                # Batch reflection at end of work cycle (if deferred)
                if defer_consolidation and self.consolidation and exchanges:
                    self._log("reflection_batch", {"exchange_count": len(exchanges)})
                    self.consolidation.append_batch(exchanges)
        finally:
            # Always release job claim and clear context
            release_job(job_id, self.id)
            self._log("job_released", {"job_id": job_id})
            self._current_job_id = None

    async def work_cycle(self):
        """Perform one cycle of autonomous work (async wrapper)."""
        return self.work_cycle_sync()
