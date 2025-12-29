"""
Profiler Agent - The Profiler

Constructs the Profile from raw Lifelog data. Extracts patterns from behavior,
not statements. The Profile schema includes:
- Identity Constraints (non-negotiables)
- Behavioral Attractors (stable patterns)
- Epistemic Style (how they handle uncertainty)
- Narrative Identity (self-concept)

Prime question: What would this person rather suffer than violate?

Temporal profiles provide biographical source data from which behavioral
patterns are extracted into the Profile.
"""

from pathlib import Path

from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.profiler import (
    ALL_PROFILER_TOOLS, ALL_PROFILER_HANDLERS,
    PROFILE_HANDLERS,
    list_temporal_profiles, get_evolution, generate_current_profile,
    get_profile, get_private_profile
)
from ..tools.shared.content_hash import (
    compute_files_hash, load_cached_hash, save_cached_hash
)

# Paths for hash-based change detection
DATA_DIR = Path(__file__).parent.parent.parent / "data"
LIFELOG_DIR = DATA_DIR / "shared" / "state" / "lifelog"
PROFILER_STATE_DIR = DATA_DIR / "profiler" / "state"
# Tracks which version of the summaries the Profiler Agent last processed
PROCESSED_SUMMARIES_HASH_FILE = PROFILER_STATE_DIR / "processed_summaries.hash"


def create_profiler_agent():
    """Create a Profiler Agent instance."""
    return create_agent(
        persona_name="profiler",
        tools=ALL_PROFILER_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Profiler Agent."""
    print("=" * 60)
    print("Euno - Profiler Agent")
    print("=" * 60)
    print("\nI construct the Profile from your Lifelog data. Behavior over belief.")
    print("Commands:")
    print("  - 'private' - Display private behavioral profile (constraints, attractors)")
    print("  - 'temporal' - List temporal profiles (biographical source data)")
    print("  - 'evolution' - Show how you evolved over time")
    print("  - 'derive' - Full pipeline: temporal profiles + behavioral extraction")
    print("  - 'extract' - Extract profile from existing temporal data")
    print("  - 'profile' - Generate current profile for other agents")
    print("  - Or ask me anything about yourself")
    print("\nType 'quit' to exit.\n")

    agent = create_profiler_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nThe synthesis evolves. So do we.")
                break

            # Handle quick commands
            if user_input.lower() == 'private':
                print(f"\n{get_private_profile()}\n")
                continue

            if user_input.lower() == 'temporal':
                print(f"\n{list_temporal_profiles()}\n")
                continue

            if user_input.lower() == 'evolution':
                print(f"\n{get_evolution()}\n")
                continue

            if user_input.lower() == 'profile':
                print(f"\n{generate_current_profile()}\n")
                continue

            if user_input.lower() == 'derive':
                print("\nDeriving temporal profiles and extracting profile...")
                result = derive_profile()
                print(f"\n{result}\n")
                continue

            if user_input.lower() == 'extract':
                print("\nExtracting behavioral profile from temporal data...")
                result = extract_behavioral_profile()
                print(f"\n{result}\n")
                continue

            response = agent.process(user_input, ALL_PROFILER_HANDLERS)
            print(f"\nProfiler: {response}\n")

        except KeyboardInterrupt:
            print("\n\nFarewell!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def derive_profile() -> str:
    """
    Derive profile with temporal profiles and behavioral extraction.

    Two-phase process:
    1. Generate temporal profiles (biographical data for each year)
    2. Extract behavioral profile from biographical data

    Returns:
        Result of the derivation and extraction process
    """
    agent = create_profiler_agent()

    # Phase 1: Generate temporal profiles from summaries
    temporal_prompt = load_prompt("profiler", "temporal")
    temporal_result = agent.process(temporal_prompt, ALL_PROFILER_HANDLERS)

    # Phase 2: Extract profile from temporal data
    extraction_prompt = load_prompt("profiler", "extract_profile")
    extraction_result = agent.process(extraction_prompt, ALL_PROFILER_HANDLERS)

    return f"Temporal profiles generated. Behavioral profile extracted.\n\n{extraction_result}"


def extract_profile() -> str:
    """
    Extract profile from existing temporal data.

    Reads temporal profiles and evolution narrative, then extracts
    the profile following the schema from docs/2_profile.md:
    - Biographical Information
    - Wants and Fears
    - Stable Attractors
    - Notable Events and Actions
    - Influences
    - Interests
    - Summary of Changes

    Writes to profile via write_private_profile().

    Returns:
        Result of extraction process
    """
    agent = create_profiler_agent()
    prompt = load_prompt("profiler", "extract_profile")
    return agent.process(prompt, ALL_PROFILER_HANDLERS)


# Backwards compatibility alias
extract_behavioral_profile = extract_profile


# Alias for backwards compatibility
derive_temporal = derive_profile
derive_synthesis = derive_profile


class AutonomousProfilerAgent(AutonomousAgent):
    """
    Autonomous Profiler Agent that maintains user's Profile over time.

    Checks:
    - Signal: logs_updated (derive profile from new data)

    Work:
    - Generate temporal profiles for each year with data
    - Track evolution of patterns over time
    - Generate current profile from temporal data

    Signals:
    - profile_updated: After deriving profile
    """

    def __init__(self):
        super().__init__(
            name="profiler",
            persona_name="profiler",
            tools=ALL_PROFILER_TOOLS,
            tool_handlers=ALL_PROFILER_HANDLERS,
            check_interval=600,  # Check every 10 minutes
            signals_on_complete=["profile_updated"]
        )

    def _get_log_files(self) -> list[Path]:
        """Get all log files across years."""
        log_files = []
        if LIFELOG_DIR.exists():
            for year_dir in LIFELOG_DIR.iterdir():
                if year_dir.is_dir() and year_dir.name.isdigit():
                    for log_file in year_dir.glob("*.md"):
                        if not log_file.name.startswith("_"):
                            log_files.append(log_file)
        return sorted(log_files)

    def _have_logs_changed(self) -> bool:
        """Check if any log files have changed since last profiling."""
        log_files = self._get_log_files()
        if not log_files:
            return False

        current_hash = compute_files_hash(log_files[-30:])  # Check recent 30 files
        cached_hash = load_cached_hash(PROCESSED_SUMMARIES_HASH_FILE)

        if cached_hash is None:
            self.logger.debug("No cached logs hash - first run")
            return True

        changed = current_hash != cached_hash
        if changed:
            self.logger.debug(f"Logs hash changed: {cached_hash[:8]}... -> {current_hash[:8]}...")
        return changed

    def _save_logs_hash(self):
        """Save current logs hash after successful profiling."""
        log_files = self._get_log_files()
        if log_files:
            current_hash = compute_files_hash(log_files[-30:])
            PROFILER_STATE_DIR.mkdir(parents=True, exist_ok=True)
            save_cached_hash(PROCESSED_SUMMARIES_HASH_FILE, current_hash)
            self.logger.debug(f"Saved logs hash: {current_hash[:8]}...")

    def check_work_needed(self) -> bool:
        """Check if profile needs updating."""
        # Check for explicit signal
        if self.check_signal("logs_updated"):
            self.logger.info("Received logs_updated signal")
            # Verify logs actually changed (signal might be stale)
            if self._have_logs_changed():
                return True
            self.logger.debug("Signal received but logs unchanged - skipping")
            return False

        # Fallback: check if logs changed without signal
        if self._have_logs_changed():
            self.logger.info("Logs changed (no signal) - profiling needed")
            return True

        return False

    def do_work(self) -> str:
        """Derive profile from lifelog data."""
        result = derive_profile()

        # Save hash so we don't re-process unchanged logs
        self._save_logs_hash()

        self.agent.clear_context()
        return "Profile derived from lifelog data"


if __name__ == "__main__":
    run_interactive()
