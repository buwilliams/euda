"""
Evolution Agent - The Evolver

Evolves the system based on synthesis of the user's identity. Watches for
synthesis updates and determines if agent identities should be refined
to better serve the user.

Two modes of operation:
1. REACTIVE: When synthesis_updated signal is received, analyze the user's
   epistemic state and propose agent identity evolutions that align better
2. PROACTIVE: Periodically analyze the system for improvement opportunities
"""

from datetime import datetime, timedelta
from pathlib import Path
from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.evolution.evolution import (
    EVOLUTION_TOOLS, EVOLUTION_HANDLERS,
    get_last_introspection, EVOLUTION_DIR
)
from ..tools.synthesis import (
    get_profile, get_synthesis_summary, get_axioms, get_all_values,
    PROFILE_TOOLS, PROFILE_HANDLERS
)
from ..tools.shared.identity import (
    IDENTITY_TOOLS, IDENTITY_HANDLERS,
    read_own_identity, read_core_identity,
    propose_identity_evolution, get_pending_evolutions
)


# State file for tracking
STATE_DIR = Path(__file__).parent.parent.parent / "data" / "agents" / "state"
CAPABILITIES_FILE = EVOLUTION_DIR / "capabilities.md"


def create_evolution_agent():
    """Create an Evolution Agent instance."""
    # Combine tools: evolution analysis + synthesis reading + identity evolution
    tools = EVOLUTION_TOOLS + PROFILE_TOOLS + IDENTITY_TOOLS
    handlers = {**EVOLUTION_HANDLERS, **PROFILE_HANDLERS, **IDENTITY_HANDLERS}

    return create_agent(
        persona_name="evolution",
        tools=tools
    )


def run_interactive():
    """Run an interactive session with the Evolution Agent."""
    print("=" * 60)
    print("Euno - Evolution Agent (The Evolver)")
    print("=" * 60)
    print("\nI evolve agent identities based on user synthesis.")
    print("Commands:")
    print("  - 'analyze' - Run a full system analysis")
    print("  - 'evolve' - Check synthesis and propose evolutions")
    print("  - 'pending' - Show pending evolution proposals")
    print("  - 'agents' - List all agents")
    print("  - 'capabilities' - Show current capabilities document")
    print("  - Or ask me anything about the system")
    print("\nType 'quit' to exit.\n")

    agent = create_evolution_agent()
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
                user_input = """Please analyze the user's synthesis and consider agent evolutions:
                1. Read the user's identity profile (get_profile)
                2. Review the user's epistemic axioms and values
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
            print(f"\nEvolver: {response}\n")

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
    agent = create_evolution_agent()
    handlers = {**EVOLUTION_HANDLERS, **PROFILE_HANDLERS, **IDENTITY_HANDLERS}
    prompt = load_prompt("evolution", "analyze_system")
    return agent.process(prompt, handlers)


def run_evolution_check() -> str:
    """
    Check if agent identities should evolve based on user synthesis.

    Returns:
        The result of the evolution check.
    """
    agent = create_evolution_agent()
    handlers = {**EVOLUTION_HANDLERS, **PROFILE_HANDLERS, **IDENTITY_HANDLERS}
    prompt = load_prompt("evolution", "check_evolution")
    return agent.process(prompt, handlers)


class AutonomousEvolutionAgent(AutonomousAgent):
    """
    Autonomous agent that evolves agent identities based on user synthesis.

    Triggers:
    1. synthesis_updated signal - User identity changed, check if agents should evolve
    2. Periodic refresh (every hour) - Analyze capabilities and look for improvements
    """

    def __init__(self, check_interval: int = 1800):  # 30 minutes default
        # Combine tools
        tools = EVOLUTION_TOOLS + PROFILE_TOOLS + IDENTITY_TOOLS
        handlers = {**EVOLUTION_HANDLERS, **PROFILE_HANDLERS, **IDENTITY_HANDLERS}

        super().__init__(
            name="evolution",
            persona_name="evolution",
            tools=tools,
            tool_handlers=handlers,
            check_interval=check_interval,
            signals_on_complete=["evolution_updated"]
        )

        # Track work modes
        self.last_analysis_time = None
        self.last_evolution_check = None
        self._pending_synthesis_check = False

    def check_work_needed(self) -> bool:
        """
        Check if evolution work is needed.

        Triggers:
        1. synthesis_updated signal - User identity changed, check for evolution opportunities
        2. code_changed signal - Code changed, update capabilities
        3. identity_evolved signal - An identity was evolved, update capabilities
        4. No capabilities document exists
        5. 1+ hours since last analysis
        """
        # PRIMARY: Check for synthesis update - trigger evolution analysis
        if self.check_signal("synthesis_updated"):
            self.logger.info("Synthesis updated - checking if agents should evolve")
            self._pending_synthesis_check = True
            return True

        # Check for code/identity change signals - update capabilities
        if self.check_signal("code_changed") or self.check_signal("identity_evolved"):
            self.logger.info("Change signal detected, analysis needed")
            return True

        # Check if capabilities file exists
        if not CAPABILITIES_FILE.exists():
            self.logger.info("No capabilities file, analysis needed")
            return True

        # Check file age - refresh if older than 1 hour
        if CAPABILITIES_FILE.exists():
            mtime = datetime.fromtimestamp(CAPABILITIES_FILE.stat().st_mtime)
            age = datetime.now() - mtime

            if age > timedelta(hours=1):
                self.logger.info(f"Capabilities file is {age} old, refresh needed")
                return True

        # First run
        if self.last_analysis_time is None:
            return True

        return False

    def do_work(self) -> str:
        """
        Perform evolution work.

        If synthesis_updated triggered us, check for agent evolution opportunities.
        Otherwise, run capabilities analysis.

        Returns:
            Status message.
        """
        results = []

        # If triggered by synthesis update, do evolution check
        if self._pending_synthesis_check:
            self.logger.info("Analyzing synthesis for evolution opportunities...")
            self._pending_synthesis_check = False

            try:
                result = run_evolution_check()
                self.last_evolution_check = datetime.now()
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
        state['analysis_count'] = state.get('analysis_count', 0) + 1
        self.save_state(state)

        return " | ".join(results) if results else "No work performed."


# Backwards compatibility aliases
AutonomousIntrospectionAgent = AutonomousEvolutionAgent
create_introspection_agent = create_evolution_agent


# Simple test
if __name__ == "__main__":
    run_interactive()
