"""
Interaction Agent - The Caring Friend

The user-facing conversational agent. Listens, adapts, encourages, challenges.
Detects intent and responds appropriately.

This agent can:
- Read and write to the life log
- Read user values (current, phase, lifetime)
- Read discovered opportunities
- Answer questions about the user's data
- Create and manage tasks and projects
- View daily task list and results
- Explain system capabilities
- Query agent activity logs (what agents are doing, task pickup status, etc.)
"""

from .base import create_agent
from ..tools.log import LOG_TOOLS, LOG_HANDLERS
from ..tools.fetch import FETCH_TOOLS, FETCH_HANDLERS
from ..tools.values import (
    get_current_values, get_phase_values, get_lifetime_values, get_all_values
)
from ..tools.world import get_opportunities
from ..tools.task import TASK_TOOLS, TASK_HANDLERS
from ..tools.project import PROJECT_TOOLS, PROJECT_HANDLERS
from ..tools.introspection import get_last_introspection, get_system_overview
from ..tools.agent_log import AGENT_LOG_TOOLS, AGENT_LOG_HANDLERS
from ..tools.conversation import CONVERSATION_TOOLS, CONVERSATION_HANDLERS


# Additional tools for reading values
VALUES_READ_TOOLS = [
    {
        "name": "get_current_values",
        "description": "Get the user's current values (rolling year focus). Use when they ask about their values or what matters to them now.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_phase_values",
        "description": "Get the user's life phase values (the chapter they're in).",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_lifetime_values",
        "description": "Get the user's lifetime values (persistent patterns).",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_all_values",
        "description": "Get all values at once (current, phase, lifetime). Use when they want a comprehensive view.",
        "input_schema": {"type": "object", "properties": {}}
    }
]

# Tools for reading opportunities
WORLD_READ_TOOLS = [
    {
        "name": "get_opportunities",
        "description": "Get discovered opportunities from the World Agent. Use when they ask about discoveries, suggestions, or things to explore.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category: event, person, place, learning, goal"
                },
                "alignment": {
                    "type": "string",
                    "enum": ["aligned", "expansive"],
                    "description": "Filter by aligned (matches values) or expansive (surprising)"
                },
                "include_surfaced": {
                    "type": "boolean",
                    "description": "Include already-shown opportunities"
                }
            }
        }
    }
]

# Tools for system self-awareness
INTROSPECTION_TOOLS = [
    {
        "name": "get_system_capabilities",
        "description": "Get a comprehensive guide of what this assistant can do. Use when the user asks 'what can you do?', 'what are your capabilities?', 'help me understand this system', or similar questions about the assistant's features.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_system_overview",
        "description": "Get a quick technical overview of the system structure (agents, tools, data flow). Use for technical questions about how the system works.",
        "input_schema": {"type": "object", "properties": {}}
    }
]

# Combined tools for the Interaction Agent
INTERACTION_TOOLS = (
    LOG_TOOLS +
    VALUES_READ_TOOLS +
    WORLD_READ_TOOLS +
    FETCH_TOOLS +
    TASK_TOOLS +
    PROJECT_TOOLS +
    INTROSPECTION_TOOLS +
    AGENT_LOG_TOOLS +
    CONVERSATION_TOOLS
)

# Handlers for tool execution
INTERACTION_HANDLERS = {
    **LOG_HANDLERS,
    **FETCH_HANDLERS,
    **TASK_HANDLERS,
    **PROJECT_HANDLERS,
    **AGENT_LOG_HANDLERS,
    **CONVERSATION_HANDLERS,
    "get_current_values": get_current_values,
    "get_phase_values": get_phase_values,
    "get_lifetime_values": get_lifetime_values,
    "get_all_values": get_all_values,
    "get_opportunities": get_opportunities,
    "get_system_capabilities": get_last_introspection,
    "get_system_overview": get_system_overview,
}


def create_interaction_agent():
    """Create an Interaction Agent instance."""
    return create_agent(
        persona_name="interaction",
        tools=INTERACTION_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Interaction Agent."""
    print("=" * 60)
    print("me·an·dus - The Caring Friend")
    print("=" * 60)
    print("\nHey. I'm here to listen, think with you, or help capture ideas.")
    print("Whatever you need right now.")
    print("\nType 'quit' to exit.\n")

    agent = create_interaction_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nTake care. I'll be here when you need me.")
                break

            response = agent.process(user_input, INTERACTION_HANDLERS)
            print(f"\nFriend: {response}\n")

        except KeyboardInterrupt:
            print("\n\nTake care!")
            break
        except Exception as e:
            print(f"\nSomething went wrong: {e}\n")


if __name__ == "__main__":
    run_interactive()
