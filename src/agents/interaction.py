"""
Interaction Agent - The Caring Friend

The user-facing conversational agent. Listens, adapts, encourages, challenges.
Detects intent and responds appropriately.

This agent can:
- Read and write to the life log
- Read user identity (values, behaviors, biographical context, relationships)
- Read discovered opportunities
- Answer questions about the user's data
- Record identity facts when user shares them (name, family, friends, etc.)
- Create and manage tasks and projects
- View daily task list and results
- Explain system capabilities
- Query agent activity logs (what agents are doing, task pickup status, etc.)
- Clear conversations and start fresh
- Load and search previous conversation history
- Analyze conversation themes over time
- Suggest activities based on understanding of user (values, discoveries, patterns)
- Emit profile observations for Synthesis Agent to integrate (behavioral patterns,
  identity constraints, failure modes, value expressions, change signals)
"""

from .base import create_agent
from ..tools.shared.log import LOG_TOOLS, LOG_HANDLERS
from ..tools.shared.guidance import GUIDANCE_TOOLS, GUIDANCE_HANDLERS, get_interaction_hints
from ..tools.shared.profile_signals import PROFILE_SIGNAL_TOOLS, PROFILE_SIGNAL_HANDLERS
from ..tools.world.fetch import FETCH_TOOLS, FETCH_HANDLERS
from ..tools.synthesis import get_profile, get_synthesis_summary
from ..tools.world.world import get_opportunities
from ..tools.worker.task import TASK_TOOLS, TASK_HANDLERS
from ..tools.worker.project import PROJECT_TOOLS, PROJECT_HANDLERS
from ..tools.evolution.evolution import get_last_introspection, get_system_overview
from ..tools.shared.agent_log import AGENT_LOG_TOOLS, AGENT_LOG_HANDLERS
from ..tools.interaction.conversation import CONVERSATION_TOOLS, CONVERSATION_HANDLERS
from ..tools.interaction.conversation_history import CONVERSATION_HISTORY_TOOLS, CONVERSATION_HISTORY_HANDLERS


# Identity tools - unified behavioral profile
IDENTITY_READ_TOOLS = [
    {
        "name": "get_profile",
        "description": "Get the full identity profile - behavioral model including identity constraints, failure modes, attractors, tradeoffs, epistemic style, and narrative identity. Use when user asks about who they are, their values, or patterns.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_synthesis_summary",
        "description": "Get a quick summary of the user's identity for context. Good for getting a brief overview.",
        "input_schema": {"type": "object", "properties": {}}
    }
]

# Identity write tools removed - profile facts are now captured via profile signals
# The emit_profile_observation tool allows recording insights that flow to Synthesis Agent
IDENTITY_WRITE_TOOLS = []

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

# Tools for system self-awareness (Euno = the collective system)
INTROSPECTION_TOOLS = [
    {
        "name": "get_system_capabilities",
        "description": "Get a comprehensive guide of what Euno (this assistant system) can do. Use when the user asks about 'Euno', 'what can you do?', 'what are your capabilities?', 'what features do you have?', or similar questions. Returns a user-friendly capabilities document.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_system_overview",
        "description": "Get a technical overview of Euno's architecture - the 7 agents, how they communicate, data flow, and system structure. Use when the user asks 'what is Euno?', 'how does this work?', 'what agents are there?', or wants to understand the system design.",
        "input_schema": {"type": "object", "properties": {}}
    }
]

# Combined tools for the Interaction Agent
INTERACTION_TOOLS = (
    LOG_TOOLS +
    IDENTITY_READ_TOOLS +
    IDENTITY_WRITE_TOOLS +
    WORLD_READ_TOOLS +
    FETCH_TOOLS +
    TASK_TOOLS +
    PROJECT_TOOLS +
    INTROSPECTION_TOOLS +
    AGENT_LOG_TOOLS +
    CONVERSATION_TOOLS +
    CONVERSATION_HISTORY_TOOLS +
    GUIDANCE_TOOLS +
    PROFILE_SIGNAL_TOOLS  # For emitting profile observations to Synthesis
)

# Handlers for tool execution
INTERACTION_HANDLERS = {
    **LOG_HANDLERS,
    **FETCH_HANDLERS,
    **TASK_HANDLERS,
    **PROJECT_HANDLERS,
    **AGENT_LOG_HANDLERS,
    **CONVERSATION_HANDLERS,
    **CONVERSATION_HISTORY_HANDLERS,
    **GUIDANCE_HANDLERS,
    **PROFILE_SIGNAL_HANDLERS,  # For emitting profile observations
    # Identity tools - unified profile
    "get_profile": get_profile,
    "get_synthesis_summary": get_synthesis_summary,
    # World tools
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
    print("Euno - The Caring Friend")
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
