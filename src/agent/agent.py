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
from .cognition.metacognition import Metacognition, AgentState, AgentPausedError, ProgressLimitExceeded, Consolidation


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
        self._current_topic_id = None
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
        from ..events import get_event_bus
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
            "triggers": ["topic:assigned"]
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

        The User agent IS Euno - it uses its own identity directly through
        the standard _build_system_prompt flow, so no special handling needed here.
        """
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

    def set_topic_context(self, topic_id: str):
        """Set the current topic context for the agent."""
        self._current_topic_id = topic_id

    def clear_topic_context(self):
        """Clear the current topic context."""
        self._current_topic_id = None

    def _get_topic_context_for_prompt(self) -> str:
        """Build topic context string for system prompt."""
        if not self._current_topic_id:
            return ""

        # Import from old tools module (still available during transition)
        from ..tools.data.topics import get_topic
        from ..tools.data.assets import list_assets, read_asset

        topic = get_topic(self._current_topic_id)
        if not topic:
            return ""

        parts = ["## Current Topic Context\n"]
        parts.append(f"**Topic:** {topic.get('name', 'Untitled')}")

        if topic.get('description'):
            parts.append(f"\n**Description:** {topic['description']}")

        if topic.get('due_date'):
            parts.append(f"\n**Due:** {topic['due_date']}")

        # Get text-based assets
        assets = list_assets(self._current_topic_id)
        text_assets = []
        for asset in assets:
            mime = asset.get('mime_type', '')
            if mime and (mime.startswith('text/') or mime in ['application/json', 'application/xml']):
                text_assets.append(asset)

        if text_assets:
            parts.append("\n\n### Attached Files\n")
            for asset in text_assets:
                content = read_asset(self._current_topic_id, asset['filename'])
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
        """Build the system prompt from identity, user context, and plugins.

        Includes:
        - Agent's identity (from identity.md)
        - User's identity (so agents know who they serve)
        - Available plugins summary

        Note: User memory is NOT auto-injected (use memory commands for specifics).

        Args:
            voice_input: Whether input came from voice (enables conversational response style)
        """
        from ..plugins import discover_plugins
        from .cognition.reasoning.prompts import render_template

        # Get available plugins (filtered by excluded_plugins)
        excluded = self.config.get("excluded_plugins", [])
        plugins = [p for p in discover_plugins() if p.name not in excluded]

        # Build plugins section
        if plugins:
            plugins_lines = ["### Available Plugins\n"]
            for plugin in plugins:
                desc = plugin.description or "(plugin)"
                plugins_lines.append(f"- **{plugin.name}**: {desc}")
            plugins_lines.append("")
            plugins_lines.append("Use `list_plugins` to see plugins, `plugin_usage(plugin)` for help,")
            plugins_lines.append("`execute_plugin(plugin, command)` to run commands.")
            plugins_text = "\n".join(plugins_lines)
        else:
            plugins_text = "No plugins available."

        # Load user identity so agents know who they serve
        user_identity = self._get_user_identity()

        prompt = render_template(
            "agent/system",
            identity=self.identity,
            user_identity=user_identity,
            tools_by_type=plugins_text  # Reuse the template variable
        )

        # Voice mode instructions
        if voice_input:
            prompt += "\n\n## Voice Response Mode\n"
            prompt += (
                "The user is speaking to you via voice. Your response will be read aloud. "
                "Respond in natural, conversational first-person speech with complete sentences. "
                "Avoid bullet points, lists, topic IDs, or formatted text."
                "Speak as if you're talking directly to the user."
            )

        return prompt

    def _get_tools(self) -> list:
        """Get tool definitions for this agent (meta-tools for plugin system)."""
        from ..plugins import get_meta_tools
        return get_meta_tools()

    # Map of euno:* topic names to tool names for direct execution
    INTERNAL_TOPIC_TOOLS = {
        "euno:consolidate": "euno_consolidate",
        "euno:quote": "euno_quote",
    }

    def _is_internal_topic(self, topic_name: str) -> bool:
        """Check if topic is an internal euno:* topic that should be executed directly.

        Internal topics bypass the LLM chat loop and execute their mapped tool directly.
        """
        for prefix in self.INTERNAL_TOPIC_TOOLS:
            if topic_name.startswith(prefix):
                return True
        return False

    def _is_topic_cancelled(self, topic_id: str) -> bool:
        """Check if a topic has been cancelled (archived or deleted) by the user.

        Called during work iterations to detect if the user has archived or deleted
        the topic while the agent was working on it.

        Returns:
            True if topic no longer exists or is no longer in 'working' status
        """
        from ..tools.data.topics import get_topic

        topic = get_topic(topic_id)
        if topic is None:
            return True  # Topic was deleted
        if topic.get("status") != "working":
            return True  # Topic was archived or otherwise changed
        return False

    def _execute_internal_topic(self, topic: dict):
        """Execute an internal euno:* topic by calling its mapped tool directly.

        Internal topics bypass the LLM chat loop entirely for efficiency.
        The tool is executed directly and the topic is completed.
        """
        from ..tools import execute_tool
        from ..tools.data.topics import complete_topic

        topic_id = topic.get("id")
        topic_name = topic.get("name", "")

        # Find matching tool
        tool_name = None
        for prefix, tool in self.INTERNAL_TOPIC_TOOLS.items():
            if topic_name.startswith(prefix):
                tool_name = tool
                break

        if not tool_name:
            self._log("internal_topic_unknown", {"topic_id": topic_id, "topic_name": topic_name})
            return

        self._log("internal_topic_start", {
            "topic_id": topic_id,
            "topic_name": topic_name,
            "tool": tool_name
        })

        try:
            # Build tool inputs based on topic
            inputs = {"agent_id": self.id, "topic_id": topic_id}

            # For euno:consolidate, extract phase from topic description
            if tool_name == "euno_consolidate":
                description = topic.get("description", "")
                if "phase: append" in description:
                    inputs["phase"] = "append"
                elif "phase: consolidate" in description:
                    inputs["phase"] = "consolidate"
                elif "phase: both" in description:
                    inputs["phase"] = "both"
                # Default to "consolidate" if not specified

            # Execute tool directly
            result = execute_tool(tool_name, inputs)

            # Complete topic
            complete_topic(topic_id)

            self._log("internal_topic_complete", {
                "topic_id": topic_id,
                "tool": tool_name,
                "result": result
            })

        except Exception as e:
            self._log("internal_topic_error", {
                "topic_id": topic_id,
                "tool": tool_name,
                "error": str(e)
            })
            # Don't re-raise - topic stays in todo for retry

    def _get_topic_prompt_type(self, topic: dict) -> str:
        """Determine which prompt template to use based on topic type.

        Returns:
            Template name for the topic assignment prompt
        """
        return "agent/topic_assignment"

    def _format_topic_prompt(self, topic: dict, remaining: int = 0) -> str:
        """Format a topic as a standardized prompt for the agent."""
        from ..tools.data.assets import list_assets
        from ..tools.data.memory import get_memory_for_prompt
        from .cognition.reasoning.prompts import render_template

        assets = list_assets(topic['id'])
        if assets:
            names = [a['filename'] for a in assets]
            attachments = f"{len(assets)} attachment(s): {', '.join(names)}"
        else:
            attachments = "No attachments"

        remaining_notice = f"({remaining} more topics waiting)" if remaining > 0 else ""

        tags = topic.get('tags', [])
        tags_str = ', '.join(tags) if tags else 'None'

        # Select prompt template based on topic type
        template_name = self._get_topic_prompt_type(topic)

        return render_template(
            template_name,
            agent_id=self.id,  # For agent-specific template lookup
            topic_id=topic.get('id'),
            topic_name=topic.get('name', 'Untitled'),
            topic_description=topic.get('description') or 'None provided',
            topic_due_date=topic.get('due_date') or 'No deadline',
            topic_tags=tags_str,
            topic_attachments=attachments,
            remaining_topics_notice=remaining_notice
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
            topic_id=self._current_topic_id
        )

        self._log("llm_response", {
            "stop_reason": response.stop_reason,
            "usage": {"input": response.usage.input_tokens, "output": response.usage.output_tokens}
        })

        # Handle tool use in a loop
        self.metacognition.reset_iteration()

        while response.stop_reason == "tool_use":
            tool_results = self._execute_tools(response)

            # Break early if done_working was called (prevents LLM from looping)
            if self._work_done:
                self._log("tool_loop_exit", {"reason": "done_working"})
                break

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = client.create(
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
                tools=tools if tools else None,
                agent_id=self.id,
                topic_id=self._current_topic_id
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

        # Log user conversations to long-term memory for the user agent
        # Only log actual user conversations, not autonomous work cycles
        if self.id == "user" and log_to_memory:
            self._append_to_long_term_memory(message, text_response)

        # Run reflection append phase to extract noteworthy items
        # Skip if defer_consolidation=True (caller will batch process)
        if self.consolidation and log_to_memory and not defer_consolidation:
            self.consolidation.append(message, text_response)

        return text_response

    def _execute_tools(self, response) -> list:
        """Execute tool calls (meta-tools for plugin system) and return results."""
        import json
        from ..plugins import execute_meta_tool
        from ..tools.system.system import set_agent_context, clear_agent_context

        # Set agent context so tools can access this agent
        set_agent_context(self)

        # Build context for meta-tools
        agent_context = {
            "agent_id": self.id,
            "topic_id": self._current_topic_id,
            "session_id": self._session_id,
            "excluded_plugins": self.config.get("excluded_plugins", [])
        }

        try:
            # Collect all tool calls
            tool_calls = [block for block in response.content if block.type == "tool_use"]
            results = []

            # Execute each tool call
            for block in tool_calls:
                self._log("tool_call", {"tool": block.name, "input": block.input})
                # Record for action/progress awareness
                self.metacognition.record_tool_call(block.name, block.input)

                # Execute meta-tool
                result = execute_meta_tool(block.name, block.input, agent_context)

                # Check for done_working signal in execute_plugin results
                if block.name == "execute_plugin":
                    plugin = block.input.get("plugin", "")
                    command = block.input.get("command", "")
                    if plugin == "core" and command.strip() == "done":
                        self._work_done = True

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

        The agent discovers, claims, works, and releases topics autonomously.
        The manager only starts agents and monitors health.

        Args:
            trigger_context: Optional event data that triggered this cycle
        """
        from ..tools.data.topics import list_topics, claim_topic, release_topic, error_topic

        self._log("work_cycle_start", {"trigger": trigger_context})
        self._work_done = False
        self.metacognition.reset_work_cycle()  # Reset tracking for new work cycle

        # Query for actionable todo topics assigned to this agent
        topics = list_topics(status="todo", assignee=self.id, actionable=True)
        if not topics:
            self._log("work_cycle_end", {"reason": "no_topics"})
            return  # Nothing to do

        self._log("work_cycle_topics_found", {"count": len(topics)})

        # Work the first topic - after completion, manager will trigger another cycle if more exist
        current_topic = topics[0]
        remaining = len(topics) - 1
        topic_id = current_topic.get("id")

        # Claim the topic exclusively (sets status to 'working')
        claim_result = claim_topic(topic_id, self.id)
        if "error" in claim_result:
            self._log("topic_claim_failed", {"topic_id": topic_id, "error": claim_result.get("error")})
            return  # Topic was claimed by another agent

        self._log("topic_claimed", {"topic_id": topic_id})

        # Set topic context for cost/rate tracking
        self._current_topic_id = topic_id

        try:
            topic_tags = current_topic.get("tags", [])
            topic_name = current_topic.get("name", "")

            # Check for internal euno:* topics first - these execute tools directly
            if self._is_internal_topic(topic_name):
                self._execute_internal_topic(current_topic)
                return

            # Use standardized topic prompt format
            from .cognition.reasoning.prompts import load_template
            prompt = self._format_topic_prompt(current_topic, remaining)

            # Strategic planning phase (if configured for this topic type)
            plan = None
            if self.metacognition.planner.should_plan(current_topic):
                self._log("planning_start", {"topic_id": current_topic.get("id")})
                plan = self.metacognition.planner.create_plan(current_topic)
                if plan:
                    prompt = self.metacognition.planner.inject_plan(prompt, plan)
                    self._log("planning_injected", {"topic_id": current_topic.get("id"), "plan_length": len(plan)})

            # Autonomous loop - keep working until agent calls done_working
            iteration = 0

            # Check if deferred reflection is enabled (efficiency optimization)
            defer_consolidation = self.metacognition.should_defer_consolidation()
            exchanges = []  # Collect for batched reflection if deferred

            # Track consecutive minimal responses to detect stuck patterns
            # (complements tool-based stuck detection for cases where no tools are called)
            consecutive_minimal_responses = 0
            MINIMAL_RESPONSE_THRESHOLD = 5  # Stop after N consecutive minimal responses
            MINIMAL_RESPONSE_LENGTH = 20  # Responses shorter than this are "minimal"

            # Start progress tracking session for stuck detection
            session_id = self.metacognition.start_work_session(session_type="work_cycle")
            self._log("work_session_started", {"session_id": session_id})

            try:
                while not self._work_done:
                    iteration += 1
                    self._log("work_iteration", {"iteration": iteration})

                    # Increment progress tracker to enforce iteration limits
                    self.metacognition.increment_iteration()

                    # Check if topic was cancelled (archived/deleted) by user
                    if iteration > 1 and self._is_topic_cancelled(topic_id):
                        self._log("topic_cancelled", {"topic_id": topic_id, "iteration": iteration})
                        print(f"[{self.id}] Topic {topic_id} was cancelled by user")
                        break

                    # Stuck detection happens automatically during tool execution
                    # via record_tool_call -> ProgressTracker.record_tool_call
                    # which raises ProgressLimitExceeded if stuck pattern detected

                    # Log to memory for memory creation, but don't save to conversation history
                    # Defer reflection if enabled (will batch process at end)
                    response = self.chat(prompt, log_to_memory=True, save_to_history=False,
                                         defer_consolidation=defer_consolidation)

                    # Detect minimal/empty responses (LLM returning "..." or similar)
                    # This catches cases where no tools are called and stuck detection won't trigger
                    response_text = response.strip() if response else ""
                    if len(response_text) < MINIMAL_RESPONSE_LENGTH:
                        consecutive_minimal_responses += 1
                        self._log("minimal_response", {
                            "iteration": iteration,
                            "response_length": len(response_text),
                            "consecutive_count": consecutive_minimal_responses
                        })
                        if consecutive_minimal_responses >= MINIMAL_RESPONSE_THRESHOLD:
                            raise ProgressLimitExceeded(
                                self.id,
                                session_id,
                                f"Agent returned {consecutive_minimal_responses} consecutive minimal responses"
                            )
                    else:
                        consecutive_minimal_responses = 0  # Reset on substantive response

                    # Collect exchange for batched reflection
                    if defer_consolidation and self.consolidation:
                        exchanges.append((prompt, response))

                    print(f"[{self.id}] {response[:100]}...")

                    if self._work_done:
                        break

                    # Continue prompt for subsequent iterations with progress context
                    progress_ctx = self.metacognition.get_progress_context()

                    # Format stuck warning if detected (safeguard check)
                    stuck_warning = ""
                    if progress_ctx.get("stuck_warning"):
                        stuck_warning = f"**Warning:** {progress_ctx['stuck_warning']}"

                    prompt = load_template("agent/continue_with_context").format(
                        iteration=progress_ctx.get("iteration", iteration),
                        tool_calls_this_cycle=progress_ctx.get("tool_calls_this_cycle", 0),
                        stuck_warning=stuck_warning
                    )

                self._log("work_cycle_end", {"reason": "done_working", "iterations": iteration})

            except ProgressLimitExceeded as e:
                # Stuck pattern detected during tool execution
                self._log("stuck_detected", {"reason": e.reason, "iteration": iteration})
                print(f"[{self.id}] Stuck detected: {e.reason}")
                # Mark topic as error (prevents release_topic from resetting to todo)
                error_topic(topic_id, f"Stuck: {e.reason}", self.id)
                # Pause agent to require manual intervention
                raise AgentPausedError(self.id, f"Stuck: {e.reason}")

            finally:
                # End progress tracking session
                session_stats = self.metacognition.end_work_session()
                if session_stats:
                    self._log("work_session_ended", session_stats)

                # Batch reflection at end of work cycle (if deferred)
                if defer_consolidation and self.consolidation and exchanges:
                    self._log("reflection_batch", {"exchange_count": len(exchanges)})
                    self.consolidation.append_batch(exchanges)
        finally:
            # Release topic claim (no-op if already completed, since in_progress_by is cleared)
            release_topic(topic_id, self.id)
            self._log("topic_released", {"topic_id": topic_id})
            self._current_topic_id = None

    async def work_cycle(self):
        """Perform one cycle of autonomous work (async wrapper)."""
        return self.work_cycle_sync()
