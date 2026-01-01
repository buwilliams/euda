"""
Adaptor Agent - The Adaptor

Refines agent identities to serve this specific user. Watches for
profile updates and determines if agent identities should be refined
to better serve the user.

Two modes of operation:
1. REACTIVE: When profile_updated signal is received, analyze the user's
   profile and propose agent identity evolutions that align better
2. PROACTIVE: Periodically analyze the system for improvement opportunities
"""

from datetime import datetime, timedelta
from pathlib import Path
from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.adaptor.evolution import (
    EVOLUTION_TOOLS, EVOLUTION_HANDLERS,
    get_last_introspection, EVOLUTION_DIR
)
from ..tools.adaptor.health import (
    HEALTH_TOOLS, HEALTH_HANDLERS,
    run_health_assessment
)
from ..tools.profiler import (
    get_profile, get_synthesis_summary,
    PROFILE_TOOLS, PROFILE_HANDLERS
)
from ..tools.shared.identity import (
    IDENTITY_TOOLS, IDENTITY_HANDLERS,
    read_own_identity, read_core_identity,
    propose_identity_evolution, get_pending_evolutions
)
from ..tools.shared.notifications import create_euno_task
from ..tools.shared.content_hash import (
    compute_directory_hash, load_cached_hash, save_cached_hash
)


# Paths for state and hash tracking
DATA_DIR = Path(__file__).parent.parent.parent / "data"
STATE_DIR = DATA_DIR / "agents" / "state"
CAPABILITIES_FILE = EVOLUTION_DIR / "capabilities.md"
PROFILER_DIR = DATA_DIR / "profiler" / "state"
ADAPTOR_STATE_DIR = DATA_DIR / "adaptor" / "state"
# Tracks which version of the profile the Adaptor Agent last processed
PROCESSED_PROFILE_HASH_FILE = ADAPTOR_STATE_DIR / "processed_profile.hash"


def create_adaptor_agent():
    """Create an Adaptor Agent instance."""
    # Combine tools: evolution analysis + profile reading + identity evolution
    tools = EVOLUTION_TOOLS + PROFILE_TOOLS + IDENTITY_TOOLS
    handlers = {**EVOLUTION_HANDLERS, **PROFILE_HANDLERS, **IDENTITY_HANDLERS}

    return create_agent(
        persona_name="adaptor",
        tools=tools
    )


def run_interactive():
    """Run an interactive session with the Adaptor Agent."""
    print("=" * 60)
    print("Euno - Adaptor Agent")
    print("=" * 60)
    print("\nI refine agent identities based on user profile.")
    print("Commands:")
    print("  - 'analyze' - Run a full system analysis")
    print("  - 'evolve' - Check profile and propose evolutions")
    print("  - 'pending' - Show pending evolution proposals")
    print("  - 'agents' - List all agents")
    print("  - 'capabilities' - Show current capabilities document")
    print("  - Or ask me anything about the system")
    print("\nType 'quit' to exit.\n")

    agent = create_adaptor_agent()
    handlers = {**EVOLUTION_HANDLERS, **PROFILE_HANDLERS, **IDENTITY_HANDLERS}

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nUntil next time.")
                break

            # Handle shortcuts
            if user_input.lower() == 'analyze':
                user_input = """Please run a full system analysis:
                1. Get the system overview
                2. List and analyze all agents
                3. List and analyze key tools modules
                4. Generate a comprehensive capabilities document
                5. Save it for future reference"""
            elif user_input.lower() == 'evolve':
                user_input = """Please analyze the user's profile and consider agent evolutions:
                1. Read the user's profile (get_profile)
                2. Review the profile (constraints, attractors, epistemic style)
                3. For each agent, read their current identity
                4. Determine if any agent identities should evolve to better serve this user
                5. If yes, propose specific identity evolutions with clear rationale"""
            elif user_input.lower() == 'pending':
                user_input = "Show me all pending identity evolution proposals"
            elif user_input.lower() == 'agents':
                user_input = "List all agents in the system"
            elif user_input.lower() == 'capabilities':
                user_input = "Show the current capabilities document"

            response = agent.process(user_input, handlers)
            print(f"\nAdaptor: {response}\n")

        except KeyboardInterrupt:
            print("\n\nUntil next time.")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def run_analysis() -> str:
    """
    Run a full system analysis and generate capabilities document.

    Returns:
        The result of the analysis.
    """
    agent = create_adaptor_agent()
    handlers = {**EVOLUTION_HANDLERS, **PROFILE_HANDLERS, **IDENTITY_HANDLERS}
    prompt = load_prompt("adaptor", "analyze_system")
    return agent.process(prompt, handlers)


def run_evolution_check() -> str:
    """
    Check if agent identities should evolve based on user profile.

    Returns:
        The result of the evolution check.
    """
    agent = create_adaptor_agent()
    handlers = {**EVOLUTION_HANDLERS, **PROFILE_HANDLERS, **IDENTITY_HANDLERS}
    prompt = load_prompt("adaptor", "check_evolution")
    return agent.process(prompt, handlers)


class AutonomousAdaptorAgent(AutonomousAgent):
    """
    Autonomous agent that refines agent identities based on user profile.

    Triggers:
    1. profile_updated signal - User profile changed, check if agents should evolve
    2. Periodic health assessment (every 6 hours) - Identify gaps and steer agents
    3. Periodic refresh (every hour) - Analyze capabilities and look for improvements
    """

    def __init__(self, check_interval: int = 1800):  # 30 minutes default
        # Combine tools (including health assessment)
        tools = EVOLUTION_TOOLS + HEALTH_TOOLS + PROFILE_TOOLS + IDENTITY_TOOLS
        handlers = {**EVOLUTION_HANDLERS, **HEALTH_HANDLERS, **PROFILE_HANDLERS, **IDENTITY_HANDLERS}

        super().__init__(
            name="adaptor",
            persona_name="adaptor",
            tools=tools,
            tool_handlers=handlers,
            check_interval=check_interval,
            signals_on_complete=["adaptor_updated"]
        )

        # Track work modes
        self.last_analysis_time = None
        self.last_evolution_check = None
        self.last_health_assessment = None
        self._pending_profile_check = False
        self._pending_health_check = False

    def _has_profile_changed(self) -> bool:
        """Check if profile content has changed since last check."""
        if not PROFILER_DIR.exists():
            return False

        # Hash the profile and temporal directories
        profile_dir = PROFILER_DIR / "profile"
        temporal_dir = PROFILER_DIR / "temporal"

        # Compute combined hash
        import hashlib
        hasher = hashlib.md5()

        for dir_path in [profile_dir, temporal_dir]:
            if dir_path.exists():
                for file_path in sorted(dir_path.glob("*.md")):
                    if not file_path.name.startswith('_'):
                        with open(file_path, 'rb') as f:
                            hasher.update(f.read())

        current_hash = hasher.hexdigest()
        cached_hash = load_cached_hash(PROCESSED_PROFILE_HASH_FILE)

        if cached_hash is None:
            self.logger.debug("No cached profile hash - first run")
            return True

        changed = current_hash != cached_hash
        if changed:
            self.logger.debug(f"Profile hash changed: {cached_hash[:8]}... -> {current_hash[:8]}...")
        return changed

    def _save_profile_hash(self):
        """Save current profile hash after successful processing."""
        if not PROFILER_DIR.exists():
            return

        import hashlib
        hasher = hashlib.md5()

        profile_dir = PROFILER_DIR / "profile"
        temporal_dir = PROFILER_DIR / "temporal"

        for dir_path in [profile_dir, temporal_dir]:
            if dir_path.exists():
                for file_path in sorted(dir_path.glob("*.md")):
                    if not file_path.name.startswith('_'):
                        with open(file_path, 'rb') as f:
                            hasher.update(f.read())

        current_hash = hasher.hexdigest()
        ADAPTOR_STATE_DIR.mkdir(parents=True, exist_ok=True)
        save_cached_hash(PROCESSED_PROFILE_HASH_FILE, current_hash)
        self.logger.debug(f"Saved profile hash: {current_hash[:8]}...")

    def check_work_needed(self) -> bool:
        """
        Check if evolution work is needed.

        Triggers:
        1. profile_updated signal - User profile changed, check for evolution opportunities
           (verified by hash check to avoid redundant work)
        2. code_changed signal - Code changed, update capabilities
        3. identity_evolved signal - An identity was evolved, update capabilities
        4. No capabilities document exists
        5. 6+ hours since last health assessment (or first run)
        """
        state = self.load_state()

        # PRIMARY: Check for profile update - trigger evolution analysis
        if self.check_signal("profile_updated"):
            self.logger.info("Profile updated signal received")
            # Verify profile actually changed
            if self._has_profile_changed():
                self._pending_profile_check = True
                return True
            self.logger.debug("Signal received but profile unchanged - skipping")

        # Check for code/identity change signals - update capabilities
        if self.check_signal("code_changed") or self.check_signal("identity_evolved"):
            self.logger.info("Change signal detected, analysis needed")
            return True

        # Check if capabilities file exists
        if not CAPABILITIES_FILE.exists():
            self.logger.info("No capabilities file, analysis needed")
            return True

        # Check health assessment age - run every 6 hours
        last_health = state.get('last_health_assessment')
        if last_health:
            try:
                last_health_dt = datetime.fromisoformat(last_health)
                if datetime.now() - last_health_dt > timedelta(hours=6):
                    self.logger.info("Health assessment due (6+ hours)")
                    self._pending_health_check = True
                    return True
            except:
                pass
        else:
            # First run - do health assessment
            self.logger.info("First health assessment needed")
            self._pending_health_check = True
            return True

        # Fallback: check if profile changed without signal
        if self._has_profile_changed():
            self.logger.info("Profile changed (no signal) - evolution check needed")
            self._pending_profile_check = True
            return True

        return False

    def do_work(self) -> str:
        """
        Perform evolution work.

        If synthesis_updated triggered us, check for agent evolution opportunities.
        If health assessment due, run health check and generate gaps/guidance.
        Otherwise, run capabilities analysis.

        Returns:
            Status message.
        """
        results = []

        # Run health assessment if needed
        if self._pending_health_check:
            self.logger.info("Running system health assessment...")
            self._pending_health_check = False

            try:
                health_result = run_health_assessment()
                self.last_health_assessment = datetime.now()
                results.append("Health assessment complete")

                # Notify about high-priority gaps
                self._notify_high_priority_gaps()
            except Exception as e:
                self.logger.error(f"Health assessment failed: {e}")
                results.append(f"Health assessment failed: {e}")

        # If triggered by profile update, do evolution check
        if self._pending_profile_check:
            self.logger.info("Analyzing profile for evolution opportunities...")
            self._pending_profile_check = False

            try:
                result = run_evolution_check()
                self.last_evolution_check = datetime.now()
                # Save hash so we don't re-process unchanged profile
                self._save_profile_hash()
                results.append(f"Evolution check complete. {len(result)} chars.")
            except Exception as e:
                self.logger.error(f"Evolution check failed: {e}")
                results.append(f"Evolution check failed: {e}")

        # Run capabilities analysis if needed
        if not CAPABILITIES_FILE.exists() or self.last_analysis_time is None:
            self.logger.info("Running system capabilities analysis...")

            try:
                result = run_analysis()
                self.last_analysis_time = datetime.now()
                results.append(f"Analysis complete. {len(result)} chars.")
            except Exception as e:
                self.logger.error(f"Analysis failed: {e}")
                results.append(f"Analysis failed: {e}")

        # Update state
        state = self.load_state()
        state['last_analysis'] = self.last_analysis_time.isoformat() if self.last_analysis_time else None
        state['last_evolution_check'] = self.last_evolution_check.isoformat() if self.last_evolution_check else None
        state['last_health_assessment'] = self.last_health_assessment.isoformat() if self.last_health_assessment else None
        state['analysis_count'] = state.get('analysis_count', 0) + 1
        self.save_state(state)

        return " | ".join(results) if results else "No work performed."

    def _notify_high_priority_gaps(self):
        """Send notification for the highest priority gap found."""
        import json
        gaps_file = Path(__file__).parent.parent.parent / "data" / "shared" / "state" / "signals" / "proactive_gaps.json"

        if not gaps_file.exists():
            return

        try:
            data = json.loads(gaps_file.read_text())
            gaps = data.get("gaps", [])

            # Find highest priority gap
            high_gaps = [g for g in gaps if g.get("priority") == "high"]
            if high_gaps:
                gap = high_gaps[0]
                create_euno_task(
                    agent_name="adaptor",
                    title=gap["question"],
                    message=gap["context"],
                    task_type="question",
                    priority="normal"
                )
        except Exception as e:
            self.logger.error(f"Failed to notify about gaps: {e}")


# Backwards compatibility aliases
AutonomousEvolutionAgent = AutonomousAdaptorAgent
AutonomousIntrospectionAgent = AutonomousAdaptorAgent
create_evolution_agent = create_adaptor_agent
create_introspection_agent = create_adaptor_agent


# Simple test
if __name__ == "__main__":
    run_interactive()
