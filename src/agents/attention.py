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
from ..tools.synthesis import PROFILE_TOOLS, PROFILE_HANDLERS
from ..tools.shared.log import LOG_TOOLS, LOG_HANDLERS
from ..tools.shared.notifications import create_euno_task
from ..tools.shared.profile_signals import PROFILE_SIGNAL_TOOLS, PROFILE_SIGNAL_HANDLERS
from ..tools.shared.content_hash import (
    compute_directory_hash, load_cached_hash, save_cached_hash
)

# Paths for proactive attention
DATA_DIR = Path(__file__).parent.parent.parent / "data"
SIGNALS_DIR = DATA_DIR / "shared" / "state" / "signals"
ATTENTION_STATE_DIR = DATA_DIR / "attention" / "state"
LIFELOG_DIR = DATA_DIR / "shared" / "state" / "lifelog"
PATTERNS_CACHE_FILE = ATTENTION_STATE_DIR / "patterns.cache.json"
ATTENTION_STATE_DIR.mkdir(parents=True, exist_ok=True)


# Combined tools - Attention agent needs access to profile (identity) and logs
ALL_TOOLS = ATTENTION_TOOLS + PROFILE_TOOLS + LOG_TOOLS + PROFILE_SIGNAL_TOOLS
ALL_HANDLERS = {**ATTENTION_HANDLERS, **PROFILE_HANDLERS, **LOG_HANDLERS, **PROFILE_SIGNAL_HANDLERS}


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
    - Actionable patterns: recurring intents that could become projects/tasks
    - Has morning/evening attention been delivered today?

    Work:
    - Generate morning attention
    - Generate evening reflection
    - Surface high-priority opportunities
    - Surface proactive questions (one at a time, with cooldowns)
    - Proactively create projects/tasks from detected patterns
    - Clean up old completed tasks

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

    # Proactive creation throttling
    PROACTIVE_CREATION_COOLDOWN = 24 * 60 * 60  # 24 hours between creations
    MAX_PROACTIVE_PER_WEEK = 3  # Maximum proactive items per week

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

    def _can_create_proactively(self) -> bool:
        """Check if proactive creation is allowed (respecting throttling)."""
        surfaced = self._load_surfaced_state()
        creations = surfaced.get("proactive_creations", [])

        now = datetime.now()

        # Check cooldown since last creation
        if creations:
            last_creation = datetime.fromisoformat(creations[-1].get("created_at", "2000-01-01"))
            if (now - last_creation).total_seconds() < self.PROACTIVE_CREATION_COOLDOWN:
                return False

        # Check weekly limit
        week_ago = now - timedelta(days=7)
        recent_creations = [
            c for c in creations
            if datetime.fromisoformat(c.get("created_at", "2000-01-01")) > week_ago
        ]
        if len(recent_creations) >= self.MAX_PROACTIVE_PER_WEEK:
            return False

        return True

    def _track_proactive_creation(self, item_type: str, title: str):
        """Track a proactive creation for throttling."""
        surfaced = self._load_surfaced_state()
        creations = surfaced.get("proactive_creations", [])

        creations.append({
            "created_at": datetime.now().isoformat(),
            "type": item_type,
            "title": title
        })

        # Keep only last 10 for cleanup
        surfaced["proactive_creations"] = creations[-10:]
        self._save_surfaced_state(surfaced)

    def _get_lifelog_hash(self) -> str:
        """Get hash of recent lifelog entries for cache validation."""
        # Hash recent log files (last 14 days would be in recent year dirs)
        import hashlib
        hasher = hashlib.md5()

        if LIFELOG_DIR.exists():
            # Get logs from last 14 days
            cutoff = datetime.now() - timedelta(days=14)
            for year_dir in sorted(LIFELOG_DIR.iterdir(), reverse=True):
                if not year_dir.is_dir() or not year_dir.name.isdigit():
                    continue
                for log_file in sorted(year_dir.glob("*.md")):
                    if log_file.name.startswith('_'):
                        continue
                    # Check if file is recent enough
                    try:
                        file_date = datetime.strptime(log_file.stem, "%Y-%m-%d")
                        if file_date.date() >= cutoff.date():
                            with open(log_file, 'rb') as f:
                                hasher.update(f.read())
                    except:
                        continue

        return hasher.hexdigest()

    def _load_patterns_cache(self) -> dict | None:
        """Load cached patterns if still valid."""
        if not PATTERNS_CACHE_FILE.exists():
            return None

        try:
            cache = json.loads(PATTERNS_CACHE_FILE.read_text())
            cached_hash = cache.get("lifelog_hash")
            current_hash = self._get_lifelog_hash()

            if cached_hash == current_hash:
                # Cache is valid
                return cache.get("patterns", [])
        except:
            pass

        return None

    def _save_patterns_cache(self, patterns: list):
        """Save patterns to cache with current lifelog hash."""
        cache = {
            "lifelog_hash": self._get_lifelog_hash(),
            "cached_at": datetime.now().isoformat(),
            "patterns": patterns
        }
        PATTERNS_CACHE_FILE.write_text(json.dumps(cache, indent=2))

    def _get_actionable_pattern(self) -> dict | None:
        """Get an actionable pattern to create proactively."""
        if not self._can_create_proactively():
            return None

        try:
            # Check cache first
            cached_patterns = self._load_patterns_cache()

            if cached_patterns is not None:
                self.logger.debug("Using cached actionable patterns")
                patterns = cached_patterns
            else:
                # Cache miss - detect patterns and cache result
                from ..tools.attention.context import detect_actionable_patterns
                patterns = detect_actionable_patterns(days=14, min_mentions=3)
                self._save_patterns_cache(patterns or [])
                self.logger.debug(f"Detected and cached {len(patterns or [])} patterns")

            if patterns:
                # Return the highest confidence pattern
                for pattern in patterns:
                    if pattern.get("confidence") in ("high", "medium"):
                        return pattern
        except Exception as e:
            self.logger.error(f"Error detecting actionable patterns: {e}")

        return None

    def _create_proactive_item(self, pattern: dict) -> str:
        """Create a project or task from a detected pattern and notify user."""
        item_type = pattern.get("type", "task")
        title = pattern.get("title", "Untitled")
        description = pattern.get("description", "")
        evidence = pattern.get("evidence", [])

        evidence_text = evidence[0] if evidence else ""

        try:
            if item_type == "project":
                from ..tools.worker.project import create_project
                result = create_project(
                    title=title,
                    description=f"Auto-created from pattern: {description}. Context: {evidence_text}",
                    project_type="goal",
                    source_agent="attention",
                    source_context=f"Detected recurring intent: {description}"
                )
            else:
                from ..tools.worker.task import create_task
                result = create_task(
                    description=title,
                    source_agent="attention",
                    source_context=f"Detected recurring intent: {description}"
                )

            # Track the creation
            self._track_proactive_creation(item_type, title)

            # Notify user via From Euno project task
            create_euno_task(
                agent_name="attention",
                title=f"Created: {title}",
                message=f"I noticed you've been thinking about this. {description}",
                task_type="notification",
                priority="normal"
            )

            self.logger.info(f"Proactively created {item_type}: {title}")
            return result

        except Exception as e:
            self.logger.error(f"Error creating proactive item: {e}")
            return f"Error creating {item_type}: {e}"

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

        # Check for actionable patterns to create proactively
        pattern = self._get_actionable_pattern()
        if pattern:
            self.logger.info(f"Found actionable pattern: {pattern.get('title')}")
            state["pending_type"] = "proactive_create"
            state["pending_pattern"] = pattern
            self.save_state(state)
            return True

        # Check if cleanup is needed (once per day during evening window)
        if self.evening_hour <= now.hour < self.evening_hour + 2:
            last_cleanup = state.get("last_task_cleanup")
            if last_cleanup != today:
                self.logger.info("Task cleanup needed")
                state["pending_type"] = "cleanup"
                self.save_state(state)
                return True

        return False

    def do_work(self) -> str:
        """Generate morning/evening attention, surface proactive question, or create items."""
        state = self.load_state()
        pending_type = state.get("pending_type", "morning")
        today = datetime.now().date().isoformat()

        if pending_type == "proactive":
            # Surface a proactive question via From Euno project task
            gap = state.get("pending_gap")
            if gap:
                create_euno_task(
                    agent_name="attention",
                    title=gap.get("question", "Quick question"),
                    message=gap.get("context", ""),
                    task_type="question",
                    priority="normal"
                )
                self._mark_gap_surfaced(gap.get("id"))
                self.logger.info(f"Surfaced proactive question: {gap.get('id')}")

            # Clear flags
            state["pending_type"] = None
            state["pending_gap"] = None
            self.save_state(state)
            return "Proactive question surfaced"

        elif pending_type == "proactive_create":
            # Create a project or task from detected pattern
            pattern = state.get("pending_pattern")
            result = "No pattern found"
            if pattern:
                result = self._create_proactive_item(pattern)

            # Clear flags
            state["pending_type"] = None
            state["pending_pattern"] = None
            self.save_state(state)
            return result

        elif pending_type == "cleanup":
            # Clean up old completed tasks
            from ..tools.worker.task import cleanup_old_completed_tasks
            result = cleanup_old_completed_tasks(retention_days=30)
            state["last_task_cleanup"] = today
            state["pending_type"] = None
            self.save_state(state)
            self.logger.info(f"Task cleanup completed: {result}")
            return result

        elif pending_type == "morning":
            result = morning_attention()
            state["last_morning_date"] = today
            state["last_morning_content"] = result
            self.logger.info("Morning attention generated")

            # Send notification via From Euno project task
            create_euno_task(
                agent_name="attention",
                title="Good morning",
                message=result,
                task_type="notification",
                priority="normal"
            )
        else:
            result = evening_attention()
            state["last_evening_date"] = today
            state["last_evening_content"] = result
            self.logger.info("Evening attention generated")

            # Send notification via From Euno project task
            create_euno_task(
                agent_name="attention",
                title="Evening reflection",
                message=result,
                task_type="notification",
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
