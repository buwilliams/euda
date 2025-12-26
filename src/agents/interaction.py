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
"""

from .base import create_agent
from ..tools.shared.log import LOG_TOOLS, LOG_HANDLERS
from ..tools.shared.guidance import GUIDANCE_TOOLS, GUIDANCE_HANDLERS, get_interaction_hints
from ..tools.world.fetch import FETCH_TOOLS, FETCH_HANDLERS
from ..tools.synthesis import (
    get_current_values, get_phase_values, get_lifetime_values, get_all_values,
    get_behaviors, get_profile, get_synthesis_summary,
    get_biographical, update_biographical,
    get_relationships, add_relationship, update_relationship
)
from ..tools.world.world import get_opportunities
from ..tools.worker.task import TASK_TOOLS, TASK_HANDLERS
from ..tools.worker.project import PROJECT_TOOLS, PROJECT_HANDLERS
from ..tools.evolution.evolution import get_last_introspection, get_system_overview
from ..tools.shared.agent_log import AGENT_LOG_TOOLS, AGENT_LOG_HANDLERS
from ..tools.interaction.conversation import CONVERSATION_TOOLS, CONVERSATION_HANDLERS
from ..tools.interaction.conversation_history import CONVERSATION_HISTORY_TOOLS, CONVERSATION_HISTORY_HANDLERS


# Identity tools - values at the core, context as support
IDENTITY_READ_TOOLS = [
    # Values (core identity)
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
        "description": "Get all values at once (current, phase, lifetime). Use when they want a comprehensive view of what matters to them.",
        "input_schema": {"type": "object", "properties": {}}
    },
    # Behaviors (derived)
    {
        "name": "get_behaviors",
        "description": "Get behavioral patterns - how the user actually acts based on observed evidence.",
        "input_schema": {"type": "object", "properties": {}}
    },
    # Profile (consolidated)
    {
        "name": "get_profile",
        "description": "Get the full identity profile - values at core, behaviors derived, context supporting.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_synthesis_summary",
        "description": "Get a quick summary of the user's identity for context.",
        "input_schema": {"type": "object", "properties": {}}
    },
    # Context (supporting, not defining)
    {
        "name": "get_biographical",
        "description": "Get biographical context (name, birth info, background). This is supporting data, not core identity.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_relationships",
        "description": "Get relationship narratives - the people who matter to the user.",
        "input_schema": {"type": "object", "properties": {}}
    }
]

# Tools for recording identity facts from conversations
IDENTITY_WRITE_TOOLS = [
    {
        "name": "update_biographical",
        "description": "Record biographical information when the user shares it (name, birth date, location, background). Use when they mention facts about themselves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "description": "Section to update: 'Name', 'Birth Date', 'Birth Place', 'Current Location', 'Background', or new"
                },
                "content": {
                    "type": "string",
                    "description": "The content for that section"
                }
            },
            "required": ["section", "content"]
        }
    },
    {
        "name": "add_relationship",
        "description": "Record a relationship when the user mentions someone important (family, friends). Use when they talk about people in their life.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The person's name"},
                "relationship_type": {"type": "string", "description": "Type: Partner, Mother, Father, Sister, Brother, Child, Friend, Colleague, etc."},
                "narrative": {"type": "string", "description": "Narrative description of this relationship"}
            },
            "required": ["name", "relationship_type", "narrative"]
        }
    },
    {
        "name": "update_relationship",
        "description": "Update the narrative for an existing relationship.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The person's name"},
                "narrative": {"type": "string", "description": "The updated narrative"}
            },
            "required": ["name", "narrative"]
        }
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
    GUIDANCE_TOOLS
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
    # Identity tools - values at core
    "get_current_values": get_current_values,
    "get_phase_values": get_phase_values,
    "get_lifetime_values": get_lifetime_values,
    "get_all_values": get_all_values,
    "get_behaviors": get_behaviors,
    "get_profile": get_profile,
    "get_synthesis_summary": get_synthesis_summary,
    "get_biographical": get_biographical,
    "update_biographical": update_biographical,
    "get_relationships": get_relationships,
    "add_relationship": add_relationship,
    "update_relationship": update_relationship,
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
