"""
Base agent pattern for Me and Us.

An agent is simply:
- A context (list of messages)
- A loop (process input → call LLM → handle tools → repeat)
- Tools (functions the agent can call)
"""

import json
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

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

    # Initialize context (messages only, system is separate)
    context = []

    # Tools default to empty list
    if tools is None:
        tools = []

    def call():
        """Make an API call to the LLM."""
        kwargs = {
            "model": model,
            "max_tokens": 8096,
            "system": system_prompt,
            "messages": context,
        }
        if tools:
            kwargs["tools"] = tools

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
                except Exception as e:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": f"Error: {str(e)}",
                        "is_error": True
                    })
            else:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": f"Unknown tool: {tool_name}",
                    "is_error": True
                })

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

        # Add user input to context
        context.append({
            "role": "user",
            "content": input_content
        })

        # Call the LLM
        response = call()

        # Handle tool calls in a loop
        while handle_tool_calls(response, tool_handlers):
            response = call()

        # Extract text response
        text_blocks = [block.text for block in response.content if hasattr(block, 'text')]
        output = "\n".join(text_blocks)

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


# Simple test
if __name__ == "__main__":
    # Test loading identity
    print("Testing identity loading...")
    identity = load_identity("ingestion")
    print(f"Loaded identity ({len(identity)} chars)")
    print(identity[:500] + "...")
