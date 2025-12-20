"""
Attention Agent - The Curator

Decides what deserves attention right now. Matches opportunities to values,
energy, and timing. Surfaces the right thing at the right moment.
"""

from datetime import datetime, time
from .base import create_agent, AutonomousAgent
from ..tools.attention import ATTENTION_TOOLS, ATTENTION_HANDLERS
from ..tools.values import VALUES_TOOLS, VALUES_HANDLERS
from ..tools.log import LOG_TOOLS, LOG_HANDLERS
from ..tools.notifications import queue_notification


# Combined tools - Attention agent needs access to values and logs too
ALL_TOOLS = ATTENTION_TOOLS + VALUES_TOOLS + LOG_TOOLS
ALL_HANDLERS = {**ATTENTION_HANDLERS, **VALUES_HANDLERS, **LOG_HANDLERS}


def create_attention_agent():
    """Create an Attention Agent instance."""
    return create_agent(
        persona_name="attention",
        tools=ALL_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Attention Agent."""
    print("=" * 60)
    print("me·an·dus - Attention Agent (The Curator)")
    print("=" * 60)
    print("\nI decide what deserves your attention right now.")
    print("Commands:")
    print("  - 'morning' - Generate morning attention")
    print("  - 'evening' - Generate evening reflection")
    print("  - 'energy' - Check/record energy state")
    print("  - 'queue' - View surfacing queue")
    print("  - Or ask me anything about attention")
    print("\nType 'quit' to exit.\n")

    agent = create_attention_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nYour attention is precious. Use it well.")
                break

            # Handle quick commands
            if user_input.lower() == 'morning':
                user_input = "Generate a morning attention message for me. Keep it brief and actionable."

            if user_input.lower() == 'evening':
                user_input = "Generate an evening reflection prompt for me. Be warm - I'm probably tired."

            if user_input.lower() == 'energy':
                user_input = "Check my current energy state and ask me about how I'm feeling across the dimensions (physical, mental, emotional, social)."

            if user_input.lower() == 'queue':
                from ..tools.attention import get_queue
                print(f"\n{get_queue()}\n")
                continue

            response = agent.process(user_input, ALL_HANDLERS)
            print(f"\nCurator: {response}\n")

        except KeyboardInterrupt:
            print("\n\nFarewell!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def morning_attention() -> str:
    """
    Generate morning attention content.

    Returns:
        Morning attention message
    """
    agent = create_attention_agent()

    prompt = """It's time for morning attention.

Use generate_morning_attention to get the context, then create a brief,
actionable morning message that:

1. Acknowledges the current time and day
2. Highlights 1-3 things that matter today
3. Considers current energy state (or asks if unknown)
4. Integrates any high-priority queue items naturally
5. Includes one thing to look forward to
6. Maintains the 90/10 balance (mostly value-aligned, with a natural surprise)

Be concise. Don't overwhelm. Start the day right.
"""

    return agent.process(prompt, ALL_HANDLERS)


def evening_attention() -> str:
    """
    Generate evening reflection prompt.

    Returns:
        Evening reflection prompt
    """
    agent = create_attention_agent()

    prompt = """It's time for evening reflection.

Use generate_evening_attention to get the context, then create a warm,
gentle evening journal prompt that:

1. Acknowledges the user is probably tired
2. Invites reflection without requiring much energy
3. Asks about subjective experience, not just facts
4. Notes something that went well (if visible in logs)
5. Creates space for what's unfinished without pressure
6. Feels like a caring friend at the end of a long day

Be warm. Be brief. Honor their tiredness.
"""

    return agent.process(prompt, ALL_HANDLERS)


class AutonomousAttentionAgent(AutonomousAgent):
    """
    Autonomous Attention Agent that triggers at key moments.

    Checks:
    - Signal: opportunities_updated
    - Time: morning window (7-9am), evening window (8-10pm)
    - Has morning/evening attention been delivered today?

    Work:
    - Generate morning attention
    - Generate evening reflection
    - Surface high-priority opportunities

    Signals:
    - attention_delivered: After generating attention content
    """

    def __init__(self, morning_hour: int = 7, evening_hour: int = 21):
        super().__init__(
            name="attention",
            persona_name="attention",
            tools=ALL_TOOLS,
            tool_handlers=ALL_HANDLERS,
            check_interval=300,  # Check every 5 minutes
            signals_on_complete=["attention_delivered"]
        )
        self.morning_hour = morning_hour
        self.evening_hour = evening_hour

    def check_work_needed(self) -> bool:
        """Check if attention is needed based on time or signals."""
        now = datetime.now()
        today = now.date().isoformat()
        state = self.load_state()

        # Check for opportunities signal - might want to surface something
        if self.check_signal("opportunities_updated"):
            self.logger.info("Received opportunities_updated signal")
            # Don't immediately act, but note it for next attention window
            state["new_opportunities"] = True
            self.save_state(state)

        # Check morning window (7-9am)
        if self.morning_hour <= now.hour < self.morning_hour + 2:
            last_morning = state.get("last_morning_date")
            if last_morning != today:
                self.logger.info("Morning attention window - generating")
                state["pending_type"] = "morning"
                self.save_state(state)
                return True

        # Check evening window (9-11pm)
        if self.evening_hour <= now.hour < self.evening_hour + 2:
            last_evening = state.get("last_evening_date")
            if last_evening != today:
                self.logger.info("Evening attention window - generating")
                state["pending_type"] = "evening"
                self.save_state(state)
                return True

        return False

    def do_work(self) -> str:
        """Generate morning or evening attention."""
        state = self.load_state()
        pending_type = state.get("pending_type", "morning")
        today = datetime.now().date().isoformat()

        if pending_type == "morning":
            result = morning_attention()
            state["last_morning_date"] = today
            state["last_morning_content"] = result
            self.logger.info("Morning attention generated")

            # Send notification to user
            queue_notification(
                agent_name="attention",
                title="Good morning",
                message=result[:200] + "..." if len(result) > 200 else result,
                notification_type="info",
                action_prompt="Tell me more about what I should focus on today",
                priority="normal"
            )
        else:
            result = evening_attention()
            state["last_evening_date"] = today
            state["last_evening_content"] = result
            self.logger.info("Evening attention generated")

            # Send notification to user
            queue_notification(
                agent_name="attention",
                title="Evening reflection",
                message=result[:200] + "..." if len(result) > 200 else result,
                notification_type="info",
                action_prompt="Let's reflect on the day",
                priority="normal"
            )

        # Clear flags
        state["pending_type"] = None
        state["new_opportunities"] = False
        self.save_state(state)

        self.agent.clear_context()
        return f"{pending_type.title()} attention delivered"

    def get_latest_attention(self) -> dict:
        """Get the most recent attention content for display."""
        state = self.load_state()
        return {
            "morning": state.get("last_morning_content"),
            "morning_date": state.get("last_morning_date"),
            "evening": state.get("last_evening_content"),
            "evening_date": state.get("last_evening_date")
        }


if __name__ == "__main__":
    run_interactive()
