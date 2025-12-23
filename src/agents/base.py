"""
Base agent pattern for Euno.

An agent is simply:
- A context (list of messages)
- A loop (process input → call LLM → handle tools → repeat)
- Tools (functions the agent can call)

Autonomous agents add:
- A check_work_needed() method to decide if work is required
- A do_work() method to perform the work
- Signal sending when work completes
- Continuous loop with idle periods
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from anthropic import Anthropic

from ..tools.identity import IDENTITY_TOOLS, IDENTITY_HANDLERS
from ..tools.agent_log import (
    log_activity, log_tool_call, log_work_check, log_work_start,
    log_work_complete, log_signal_sent, log_error
)

# Load environment variables from .env file (use explicit path, override existing)
ENV_FILE = Path(__file__).parent.parent.parent / ".env"
load_dotenv(ENV_FILE, override=True)

# Initialize client
client = Anthropic()

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent / "data"
IDENTITY_DIR = DATA_DIR / "agents" / "identity"


def load_file(path: Path) -> str:
    """Load a file's contents."""
    with open(path, 'r') as f:
        return f.read()


def load_identity(persona_name: str) -> str:
    """Load core identity + agent-specific persona."""
    core = load_file(IDENTITY_DIR / "_core.identity.md")
    persona = load_file(IDENTITY_DIR / f"{persona_name}.identity.md")
    return f"{core}\n\n---\n\n{persona}"


def create_agent(persona_name: str, tools: list = None, model: str = "claude-sonnet-4-20250514"):
    """
    Create an agent with identity loaded from file.

    Args:
        persona_name: Name of the persona file (without .identity.md)
        tools: List of tool definitions for the agent
        model: Model to use (default: claude-sonnet-4-20250514)

    Returns:
        A process function that handles conversations with this agent
    """
    # Load identity
    system_prompt = load_identity(persona_name)

    # Add current date context and agent name
    today = datetime.now().strftime('%Y-%m-%d')
    system_prompt += f"\n\n---\n\nToday's date is {today}. Use this when referencing 'today' or recent dates."
    system_prompt += f"\n\nYour agent name is '{persona_name}'. Use this when reading or proposing changes to your identity."

    # Initialize context (messages only, system is separate)
    context = []

    # Tools default to empty list, always include identity tools
    if tools is None:
        tools = []
    all_tools = tools + IDENTITY_TOOLS

    def call():
        """Make an API call to the LLM."""
        kwargs = {
            "model": model,
            "max_tokens": 8096,
            "system": system_prompt,
            "messages": context,
        }
        if all_tools:
            kwargs["tools"] = all_tools

        return client.messages.create(**kwargs)

    def handle_tool_calls(response, tool_handlers: dict):
        """
        Handle any tool calls in the response.

        Args:
            response: The API response
            tool_handlers: Dict mapping tool names to handler functions

        Returns:
            True if there were tool calls to handle, False otherwise
        """
        tool_calls = [block for block in response.content if block.type == "tool_use"]

        if not tool_calls:
            return False

        # Add assistant's response with tool calls to context
        context.append({
            "role": "assistant",
            "content": response.content
        })

        # Process each tool call
        tool_results = []
        for tool_call in tool_calls:
            tool_name = tool_call.name
            tool_input = tool_call.input

            if tool_name in tool_handlers:
                try:
                    result = tool_handlers[tool_name](**tool_input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": str(result)
                    })
                    # Log successful tool call
                    log_tool_call(persona_name, tool_name, tool_input, str(result)[:200], success=True)
                except Exception as e:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": f"Error: {str(e)}",
                        "is_error": True
                    })
                    # Log failed tool call
                    log_tool_call(persona_name, tool_name, tool_input, str(e), success=False)
            else:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": f"Unknown tool: {tool_name}",
                    "is_error": True
                })
                log_tool_call(persona_name, tool_name, tool_input, f"Unknown tool: {tool_name}", success=False)

        # Add tool results to context
        context.append({
            "role": "user",
            "content": tool_results
        })

        return True

    def process(input_content: str, tool_handlers: dict = None) -> str:
        """
        Process user input and return agent response.

        Args:
            input_content: The user's input
            tool_handlers: Dict mapping tool names to handler functions

        Returns:
            The agent's text response
        """
        if tool_handlers is None:
            tool_handlers = {}

        # Merge with identity handlers so identity tools always work
        all_handlers = {**tool_handlers, **IDENTITY_HANDLERS}

        # Add user input to context
        context.append({
            "role": "user",
            "content": input_content
        })

        # Call the LLM
        response = call()

        # Accumulate text from all responses (agent may return text alongside tool calls)
        all_text_blocks = []

        # Handle tool calls in a loop
        while handle_tool_calls(response, all_handlers):
            # Collect any text from this response before processing tools
            text_blocks = [block.text for block in response.content if hasattr(block, 'text')]
            all_text_blocks.extend(text_blocks)
            response = call()

        # Extract text from final response
        text_blocks = [block.text for block in response.content if hasattr(block, 'text')]
        all_text_blocks.extend(text_blocks)

        output = "\n".join(all_text_blocks)

        # Add assistant response to context
        context.append({
            "role": "assistant",
            "content": output
        })

        return output

    def get_context():
        """Return the current context for inspection."""
        return context

    def clear_context():
        """Clear the conversation context."""
        context.clear()

    # Return an object with all methods
    class Agent:
        pass

    agent = Agent()
    agent.process = process
    agent.get_context = get_context
    agent.clear_context = clear_context
    agent.persona = persona_name
    agent.system_prompt = system_prompt

    return agent


# ============== Autonomous Agent Base ==============

# Signals directory
SIGNALS_DIR = DATA_DIR / "agents" / "signals"
STATE_DIR = DATA_DIR / "agents" / "state"
SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)


class AutonomousAgent(ABC):
    """
    Base class for autonomous agents that run continuously.

    Each agent:
    1. Wakes on trigger or interval
    2. Checks if work is needed
    3. Does work if needed
    4. Signals downstream agents
    5. Idles until next check
    """

    def __init__(
        self,
        name: str,
        persona_name: str,
        tools: list = None,
        tool_handlers: dict = None,
        check_interval: int = 60,
        signals_on_complete: list = None
    ):
        self.name = name
        self.persona_name = persona_name
        self.tools = tools or []
        self.tool_handlers = tool_handlers or {}
        self.check_interval = check_interval
        self.signals_on_complete = signals_on_complete or []

        self.logger = logging.getLogger(f"agent.{name}")
        self.running = False
        self.last_work_time: Optional[datetime] = None
        self.work_count = 0
        self.error_count = 0

        # Create the underlying agent
        self.agent = create_agent(persona_name, tools)

        # State file for tracking
        self.state_file = STATE_DIR / f"{name}.state.json"

    @abstractmethod
    def check_work_needed(self) -> bool:
        """
        Check if work is needed.

        Each agent implements this to decide whether to do work.
        Examples:
        - Ingestion: Are there files in the inbox?
        - Summary: Have logs changed since last summary?
        - Values: Have summaries changed since last derivation?

        Returns:
            True if work is needed, False otherwise
        """
        pass

    @abstractmethod
    def do_work(self) -> str:
        """
        Perform the agent's work.

        Returns:
            A status message describing what was done
        """
        pass

    def load_state(self) -> dict:
        """Load agent state from file."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {}

    def save_state(self, state: dict):
        """Save agent state to file."""
        state['updated'] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def send_signal(self, signal_name: str):
        """Send a signal to trigger other agents."""
        signal_file = SIGNALS_DIR / f"{signal_name}.signal"
        signal_file.write_text(datetime.now().isoformat())
        self.logger.info(f"Sent signal: {signal_name}")
        log_signal_sent(self.name, signal_name)

    def check_signal(self, signal_name: str) -> bool:
        """Check if a signal exists (and consume it)."""
        signal_file = SIGNALS_DIR / f"{signal_name}.signal"
        if signal_file.exists():
            signal_file.unlink()
            return True
        return False

    async def run_once(self) -> bool:
        """
        Run one iteration of the agent loop.

        Returns:
            True if work was done, False otherwise
        """
        try:
            # Run blocking check in thread pool to not block event loop
            loop = asyncio.get_event_loop()
            work_needed = await loop.run_in_executor(None, self.check_work_needed)
            log_work_check(self.name, work_needed)

            if work_needed:
                self.logger.info(f"Work needed, starting...")
                log_work_start(self.name, f"{self.name} autonomous work")

                # Run blocking work in thread pool to not block event loop
                result = await loop.run_in_executor(None, self.do_work)
                self.last_work_time = datetime.now()
                self.work_count += 1
                self.logger.info(f"Work complete: {result}")
                log_work_complete(self.name, result[:200] if result else "completed")

                # Send completion signals
                for signal in self.signals_on_complete:
                    self.send_signal(signal)

                return True
            return False

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error during work: {e}")
            log_error(self.name, str(e))
            return False

    async def run(self):
        """Run the agent continuously."""
        self.running = True
        self.logger.info(f"Starting autonomous agent: {self.name}")

        while self.running:
            await self.run_once()
            await asyncio.sleep(self.check_interval)

        self.logger.info(f"Agent stopped: {self.name}")

    def stop(self):
        """Stop the agent."""
        self.running = False

    def get_status(self) -> dict:
        """Get agent status."""
        return {
            "name": self.name,
            "running": self.running,
            "last_work_time": self.last_work_time.isoformat() if self.last_work_time else None,
            "work_count": self.work_count,
            "error_count": self.error_count,
            "check_interval": self.check_interval
        }


# Simple test
if __name__ == "__main__":
    # Test loading identity
    print("Testing identity loading...")
    identity = load_identity("ingestion")
    print(f"Loaded identity ({len(identity)} chars)")
    print(identity[:500] + "...")
