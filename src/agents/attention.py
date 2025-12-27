"""
Attention Agent - The Curator

Decides what deserves attention right now. Matches opportunities to values,
energy, and timing. Surfaces the right thing at the right moment.

Also handles proactive attention - surfacing questions and guidance to help
the user configure and understand the system.

Can emit profile observations for Synthesis Agent to integrate (behavioral
patterns around attention, energy, and engagement).
"""

import json
from datetime import datetime, time, timedelta
from pathlib import Path
from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.attention.attention import ATTENTION_TOOLS, ATTENTION_HANDLERS
from ..tools.synthesis import VALUES_TOOLS, VALUES_HANDLERS, PROFILE_TOOLS, PROFILE_HANDLERS
from ..tools.shared.log import LOG_TOOLS, LOG_HANDLERS
from ..tools.shared.notifications import queue_notification
from ..tools.shared.profile_signals import PROFILE_SIGNAL_TOOLS, PROFILE_SIGNAL_HANDLERS

# Paths for proactive attention
DATA_DIR = Path(__file__).parent.parent.parent / "data"
SIGNALS_DIR = DATA_DIR / "shared" / "signals"
ATTENTION_STATE_DIR = DATA_DIR / "attention" / "state"
ATTENTION_STATE_DIR.mkdir(parents=True, exist_ok=True)


# Combined tools - Attention agent needs access to identity (values core) and logs
ALL_TOOLS = ATTENTION_TOOLS + VALUES_TOOLS + PROFILE_TOOLS + LOG_TOOLS + PROFILE_SIGNAL_TOOLS
ALL_HANDLERS = {**ATTENTION_HANDLERS, **VALUES_HANDLERS, **PROFILE_HANDLERS, **LOG_HANDLERS, **PROFILE_SIGNAL_HANDLERS}


def create_attention_agent():
    """Create an Attention Agent instance."""
    return create_agent(
        persona_name="attention",
        tools=ALL_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Attention Agent."""
    print("=" * 60)
    print("Euno - Attention Agent (The Curator)")
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
                from ..tools.attention.attention import get_queue
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
    prompt = load_prompt("attention", "morning")
    return agent.process(prompt, ALL_HANDLERS)


def evening_attention() -> str:
    """
    Generate evening reflection prompt.

    Returns:
        Evening reflection prompt
    """
    agent = create_attention_agent()
    prompt = load_prompt("attention", "evening")
    return agent.process(prompt, ALL_HANDLERS)


class AutonomousAttentionAgent(AutonomousAgent):
    """
    Autonomous Attention Agent that triggers at key moments.

    Checks:
    - Signal: opportunities_updated
    - Time: morning window (7-9am), evening window (8-10pm)
    - Proactive gaps: questions to ask the user
    - Has morning/evening attention been delivered today?

    Work:
    - Generate morning attention
    - Generate evening reflection
    - Surface high-priority opportunities
    - Surface proactive questions (one at a time, with cooldowns)

    Signals:
    - attention_delivered: After generating attention content
    """

    # Cooldown hours for each gap type
    GAP_COOLDOWNS = {
        "biographical.name": 168,      # 1 week
        "biographical.location": 168,  # 1 week
        "biographical.relationships": 336,  # 2 weeks
        "config.energy_baseline": 24,  # 1 day
    }

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

    def _load_surfaced_state(self) -> dict:
        """Load state tracking what's been surfaced to user."""
        surfaced_file = ATTENTION_STATE_DIR / "surfaced.json"
        if surfaced_file.exists():
            try:
                return json.loads(surfaced_file.read_text())
            except:
                pass
        return {"questions_asked": {}, "capabilities_explained": [], "progress_shown_at": None}

    def _save_surfaced_state(self, surfaced: dict):
        """Save surfaced state."""
        surfaced_file = ATTENTION_STATE_DIR / "surfaced.json"
        surfaced_file.write_text(json.dumps(surfaced, indent=2))

    def _get_gap_to_surface(self) -> dict | None:
        """
        Check gaps signal and find one to surface (respecting cooldowns).

        Returns:
            Gap dict to surface, or None if nothing should be surfaced.
        """
        gaps_file = SIGNALS_DIR / "proactive_gaps.json"
        if not gaps_file.exists():
            return None

        try:
            data = json.loads(gaps_file.read_text())
            gaps = data.get("gaps", [])
        except:
            return None

        if not gaps:
            return None

        surfaced = self._load_surfaced_state()
        questions_asked = surfaced.get("questions_asked", {})

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda g: priority_order.get(g.get("priority", "low"), 2))

        now = datetime.now()

        for gap in gaps:
            gap_id = gap.get("id")
            if not gap_id:
                continue

            # Check if this gap was recently surfaced
            asked_info = questions_asked.get(gap_id, {})
            last_asked = asked_info.get("last_asked")

            if last_asked:
                try:
                    last_asked_dt = datetime.fromisoformat(last_asked)
                    cooldown_hours = self.GAP_COOLDOWNS.get(gap_id, 72)  # Default 3 days
                    if now - last_asked_dt < timedelta(hours=cooldown_hours):
                        continue  # Still in cooldown
                except:
                    pass

            # This gap can be surfaced
            return gap

        return None

    def _mark_gap_surfaced(self, gap_id: str, answered: bool = False):
        """Mark a gap as having been surfaced."""
        surfaced = self._load_surfaced_state()
        questions_asked = surfaced.get("questions_asked", {})

        now = datetime.now().isoformat()
        if gap_id not in questions_asked:
            questions_asked[gap_id] = {
                "first_asked": now,
                "last_asked": now,
                "times_asked": 1,
                "answered": answered
            }
        else:
            questions_asked[gap_id]["last_asked"] = now
            questions_asked[gap_id]["times_asked"] = questions_asked[gap_id].get("times_asked", 0) + 1
            if answered:
                questions_asked[gap_id]["answered"] = True

        surfaced["questions_asked"] = questions_asked
        self._save_surfaced_state(surfaced)

    def check_work_needed(self) -> bool:
        """Check if attention is needed based on time, signals, or proactive gaps."""
        now = datetime.now()
        today = now.date().isoformat()
        state = self.load_state()

        # Check for opportunities signal - might want to surface something
        if self.check_signal("opportunities_updated"):
            self.logger.info("Received opportunities_updated signal")
            # Don't immediately act, but note it for next attention window
            state["new_opportunities"] = True
            self.save_state(state)

        # Check for identity signal - values have been updated
        if self.check_signal("synthesis_updated"):
            self.logger.info("Received synthesis_updated signal")
            state["identity_refreshed"] = True
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

        # Check for proactive gaps to surface
        gap = self._get_gap_to_surface()
        if gap:
            self.logger.info(f"Found gap to surface: {gap.get('id')}")
            state["pending_type"] = "proactive"
            state["pending_gap"] = gap
            self.save_state(state)
            return True

        return False

    def do_work(self) -> str:
        """Generate morning/evening attention or surface proactive question."""
        state = self.load_state()
        pending_type = state.get("pending_type", "morning")
        today = datetime.now().date().isoformat()

        if pending_type == "proactive":
            # Surface a proactive question
            gap = state.get("pending_gap")
            if gap:
                queue_notification(
                    agent_name="attention",
                    title=gap.get("question", "Quick question"),
                    message=gap.get("context", ""),
                    notification_type="question",
                    action_prompt=gap.get("action_prompt", gap.get("question")),
                    priority="normal",
                    data={"gap_id": gap.get("id")}
                )
                self._mark_gap_surfaced(gap.get("id"))
                self.logger.info(f"Surfaced proactive question: {gap.get('id')}")

            # Clear flags
            state["pending_type"] = None
            state["pending_gap"] = None
            self.save_state(state)
            return "Proactive question surfaced"

        elif pending_type == "morning":
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
