"""
Synthesis Agent - The Keeper

Constructs a PREDICTIVE IDENTITY MODEL to anticipate user behavior,
especially under stress, uncertainty, or change.

Models HOW THE USER WILL ACT, not how they wish to be seen.

Identity Stack (ordered by predictive power):
1. Identity Constraints (primary) - Non-negotiable rules revealed by sacrifice/refusal
2. Failure Modes (primary) - Predictable breakdowns under stress
3. Behavioral Attractors - Stable patterns across contexts
4. Utility Tradeoff Curves - What gets sacrificed first when goals conflict
5. Epistemic Style (supporting) - How uncertainty, revision, authority handled
6. Narrative Identity (supporting) - Self-concept, aspirational framing

Prime question: What would this person rather suffer than violate?

Temporal profiles provide biographical source data from which behavioral
patterns are extracted into the contract-compliant private profile.
"""

from pathlib import Path

from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.synthesis import (
    ALL_SYNTHESIS_TOOLS, ALL_SYNTHESIS_HANDLERS,
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
SYNTHESIS_STATE_DIR = DATA_DIR / "synthesis" / "state"
# Tracks which version of the summaries the Synthesis Agent last processed
PROCESSED_SUMMARIES_HASH_FILE = SYNTHESIS_STATE_DIR / "processed_summaries.hash"


def create_synthesis_agent():
    """Create a Synthesis Agent instance."""
    return create_agent(
        persona_name="synthesis",
        tools=ALL_SYNTHESIS_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Synthesis Agent."""
    print("=" * 60)
    print("Euno - Synthesis Agent (The Keeper)")
    print("=" * 60)
    print("\nI construct a predictive model of who you are. Behavior over belief.")
    print("Commands:")
    print("  - 'private' - Display private behavioral profile (constraints, failure modes)")
    print("  - 'temporal' - List temporal profiles (biographical source data)")
    print("  - 'evolution' - Show how you evolved over time")
    print("  - 'derive' - Full pipeline: temporal profiles + behavioral extraction")
    print("  - 'extract' - Extract behavioral profile from existing temporal data")
    print("  - 'profile' - Generate current profile for other agents")
    print("  - Or ask me anything about yourself")
    print("\nType 'quit' to exit.\n")

    agent = create_synthesis_agent()

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
                print("\nDeriving temporal profiles and extracting behavioral model...")
                result = derive_synthesis()
                print(f"\n{result}\n")
                continue

            if user_input.lower() == 'extract':
                print("\nExtracting behavioral profile from temporal data...")
                result = extract_behavioral_profile()
                print(f"\n{result}\n")
                continue

            response = agent.process(user_input, ALL_SYNTHESIS_HANDLERS)
            print(f"\nKeeper: {response}\n")

        except KeyboardInterrupt:
            print("\n\nFarewell!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def derive_synthesis() -> str:
    """
    Derive synthesis model with temporal profiles and behavioral extraction.

    Two-phase process:
    1. Generate temporal profiles (biographical data for each year)
    2. Extract behavioral profile (predictive model from biographical data)

    Returns:
        Result of the derivation and extraction process
    """
    agent = create_synthesis_agent()

    # Phase 1: Generate temporal profiles from summaries
    temporal_prompt = load_prompt("synthesis", "temporal")
    temporal_result = agent.process(temporal_prompt, ALL_SYNTHESIS_HANDLERS)

    # Phase 2: Extract behavioral profile from temporal data
    extraction_prompt = load_prompt("synthesis", "extract_behavioral")
    extraction_result = agent.process(extraction_prompt, ALL_SYNTHESIS_HANDLERS)

    return f"Temporal profiles generated. Behavioral profile extracted.\n\n{extraction_result}"


def extract_behavioral_profile() -> str:
    """
    Extract behavioral profile from existing temporal data.

    Reads temporal profiles and evolution narrative, then extracts:
    - Identity constraints (revealed by sacrifice/refusal)
    - Failure modes (stress → response patterns)
    - Behavioral attractors (stable patterns)
    - Utility tradeoff curves (sacrifice ordering)
    - Epistemic style (uncertainty handling)
    - Narrative identity (self-concept)

    Writes to contract-compliant private profile via write_private_profile().

    Returns:
        Result of extraction process
    """
    agent = create_synthesis_agent()
    prompt = load_prompt("synthesis", "extract_behavioral")
    return agent.process(prompt, ALL_SYNTHESIS_HANDLERS)


# Alias for backwards compatibility
derive_temporal = derive_synthesis


class AutonomousSynthesisAgent(AutonomousAgent):
    """
    Autonomous Synthesis Agent that maintains user's identity model over time.

    Checks:
    - Signal: summaries_updated (derive model)

    Work:
    - Generate temporal profiles for each year with data
    - Track evolution of values, beliefs, influences over time
    - Synthesize evolution narrative
    - Generate current profile from temporal data

    Signals:
    - synthesis_updated: After deriving model
    """

    def __init__(self):
        super().__init__(
            name="synthesis",
            persona_name="synthesis",
            tools=ALL_SYNTHESIS_TOOLS,
            tool_handlers=ALL_SYNTHESIS_HANDLERS,
            check_interval=600,  # Check every 10 minutes
            signals_on_complete=["synthesis_updated"]
        )

    def _get_summary_files(self) -> list[Path]:
        """Get all summary files across years."""
        summary_files = []
        if LIFELOG_DIR.exists():
            for year_dir in LIFELOG_DIR.iterdir():
                if year_dir.is_dir() and year_dir.name.isdigit():
                    summary_file = year_dir / "_summary.md"
                    if summary_file.exists():
                        summary_files.append(summary_file)
        return sorted(summary_files)

    def _have_summaries_changed(self) -> bool:
        """Check if any summary files have changed since last synthesis."""
        summary_files = self._get_summary_files()
        if not summary_files:
            return False

        current_hash = compute_files_hash(summary_files)
        cached_hash = load_cached_hash(PROCESSED_SUMMARIES_HASH_FILE)

        if cached_hash is None:
            self.logger.debug("No cached summaries hash - first run")
            return True

        changed = current_hash != cached_hash
        if changed:
            self.logger.debug(f"Summaries hash changed: {cached_hash[:8]}... -> {current_hash[:8]}...")
        return changed

    def _save_summaries_hash(self):
        """Save current summaries hash after successful synthesis."""
        summary_files = self._get_summary_files()
        if summary_files:
            current_hash = compute_files_hash(summary_files)
            SYNTHESIS_STATE_DIR.mkdir(parents=True, exist_ok=True)
            save_cached_hash(PROCESSED_SUMMARIES_HASH_FILE, current_hash)
            self.logger.debug(f"Saved summaries hash: {current_hash[:8]}...")

    def check_work_needed(self) -> bool:
        """Check if synthesis model needs updating."""
        # Check for explicit signal
        if self.check_signal("summaries_updated"):
            self.logger.info("Received summaries_updated signal")
            # Verify summaries actually changed (signal might be stale)
            if self._have_summaries_changed():
                return True
            self.logger.debug("Signal received but summaries unchanged - skipping")
            return False

        # Fallback: check if summaries changed without signal
        if self._have_summaries_changed():
            self.logger.info("Summaries changed (no signal) - synthesis needed")
            return True

        return False

    def do_work(self) -> str:
        """Derive temporal profiles and evolution narrative from summaries."""
        result = derive_synthesis()

        # Save hash so we don't re-process unchanged summaries
        self._save_summaries_hash()

        self.agent.clear_context()
        return "Temporal profiles and evolution narrative derived from summaries"


if __name__ == "__main__":
    run_interactive()
