"""
Identity evolution tools for agents to read and propose changes to their identities.

Agents can:
1. Read their current identity
2. Propose a restructured identity with rationale
3. Proposals go to an approval queue for human review
"""

import json
from datetime import datetime
from pathlib import Path

# Base paths - Agents dir is shared, evolution proposals are separate
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SHARED_DIR = DATA_DIR / "shared"
AGENTS_DIR = SHARED_DIR / "state" / "agents"
EVOLUTION_DIR = SHARED_DIR / "state" / "evolution"
EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)

# Agent name to file number mapping
AGENT_FILE_MAP = {
    "archivist": "1_archivist",
    "profiler": "2_profiler",
    "curator": "3_curator",
    "friend": "4_friend",
    "worker": "5_worker",
    "adaptor": "6_adaptor",
}


def read_own_identity(agent_name: str) -> str:
    """
    Read the agent's current agent file.

    Args:
        agent_name: Name of the agent (e.g., 'friend', 'archivist')

    Returns:
        The full content of the agent file
    """
    file_prefix = AGENT_FILE_MAP.get(agent_name, agent_name)
    agent_file = AGENTS_DIR / f"{file_prefix}.agent.md"

    if not agent_file.exists():
        return f"Error: No agent file found for agent '{agent_name}'"

    with open(agent_file, 'r') as f:
        return f.read()


def read_core_identity() -> str:
    """
    Read the core agent file that all agents inherit.

    Returns:
        The full content of the core agent file
    """
    core_file = AGENTS_DIR / "0_core.agent.md"

    if not core_file.exists():
        return "Error: Core agent file not found"

    with open(core_file, 'r') as f:
        return f.read()


def propose_identity_evolution(
    agent_name: str,
    new_identity: str,
    rationale: str,
    evolution_type: str = "refinement"
) -> str:
    """
    Propose a restructured identity for human approval.

    The proposal is stored in the evolution queue. The human can review,
    approve, or reject the proposed changes.

    Args:
        agent_name: Name of the agent proposing the change
        new_identity: The complete new identity content (markdown)
        rationale: Explanation of what changed and why
        evolution_type: Type of change - 'refinement', 'learning', 'restructure'

    Returns:
        Confirmation that the proposal was queued
    """
    # Create proposal
    proposal = {
        "agent_name": agent_name,
        "proposed_at": datetime.now().isoformat(),
        "evolution_type": evolution_type,
        "rationale": rationale,
        "new_identity": new_identity,
        "status": "pending"
    }

    # Save to evolution queue
    proposal_file = EVOLUTION_DIR / f"{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(proposal_file, 'w') as f:
        json.dump(proposal, f, indent=2)

    return f"Identity evolution proposed. Awaiting human approval.\n\nRationale: {rationale}"


def get_pending_evolutions(agent_name: str = "") -> str:
    """
    Get pending identity evolution proposals.

    Args:
        agent_name: Optional filter by agent name

    Returns:
        List of pending proposals
    """
    proposals = []

    for f in sorted(EVOLUTION_DIR.glob("*.json")):
        with open(f, 'r') as file:
            proposal = json.load(file)

        if proposal.get("status") != "pending":
            continue

        if agent_name and proposal.get("agent_name") != agent_name:
            continue

        proposals.append({
            "file": f.name,
            "agent": proposal.get("agent_name"),
            "type": proposal.get("evolution_type"),
            "proposed_at": proposal.get("proposed_at"),
            "rationale": proposal.get("rationale")
        })

    if not proposals:
        return "No pending identity evolution proposals."

    result = f"Found {len(proposals)} pending proposal(s):\n\n"
    for p in proposals:
        result += f"**{p['agent']}** ({p['type']})\n"
        result += f"  Proposed: {p['proposed_at'][:16]}\n"
        result += f"  Rationale: {p['rationale'][:200]}...\n"
        result += f"  File: {p['file']}\n\n"

    return result


def review_evolution(filename: str) -> str:
    """
    Review a specific evolution proposal.

    Args:
        filename: The proposal filename

    Returns:
        Full proposal details including the new identity content
    """
    proposal_file = EVOLUTION_DIR / filename

    if not proposal_file.exists():
        return f"Error: Proposal '{filename}' not found"

    with open(proposal_file, 'r') as f:
        proposal = json.load(f)

    # Get current identity for comparison
    current = read_own_identity(proposal["agent_name"])

    result = f"# Evolution Proposal: {proposal['agent_name']}\n\n"
    result += f"**Type:** {proposal['evolution_type']}\n"
    result += f"**Proposed:** {proposal['proposed_at']}\n"
    result += f"**Status:** {proposal['status']}\n\n"
    result += f"## Rationale\n\n{proposal['rationale']}\n\n"
    result += f"## Proposed New Identity\n\n{proposal['new_identity']}\n\n"
    result += f"---\n\n## Current Identity (for reference)\n\n{current}"

    return result


def approve_evolution(filename: str) -> str:
    """
    Approve and apply an identity evolution.

    Args:
        filename: The proposal filename

    Returns:
        Confirmation of the applied changes
    """
    proposal_file = EVOLUTION_DIR / filename

    if not proposal_file.exists():
        return f"Error: Proposal '{filename}' not found"

    with open(proposal_file, 'r') as f:
        proposal = json.load(f)

    if proposal.get("status") != "pending":
        return f"Error: Proposal is not pending (status: {proposal.get('status')})"

    agent_name = proposal["agent_name"]
    file_prefix = AGENT_FILE_MAP.get(agent_name, agent_name)
    agent_file = AGENTS_DIR / f"{file_prefix}.agent.md"

    # Backup current agent file
    if agent_file.exists():
        backup_dir = EVOLUTION_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_file = backup_dir / f"{file_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(agent_file, 'r') as f:
            backup_content = f.read()
        with open(backup_file, 'w') as f:
            f.write(backup_content)

    # Apply new agent content
    with open(agent_file, 'w') as f:
        f.write(proposal["new_identity"])

    # Update proposal status
    proposal["status"] = "approved"
    proposal["approved_at"] = datetime.now().isoformat()
    with open(proposal_file, 'w') as f:
        json.dump(proposal, f, indent=2)

    return f"Identity evolution approved and applied for {agent_name}.\nBackup saved to evolution/backups/"


def reject_evolution(filename: str, reason: str = "") -> str:
    """
    Reject an identity evolution proposal.

    Args:
        filename: The proposal filename
        reason: Optional reason for rejection

    Returns:
        Confirmation of rejection
    """
    proposal_file = EVOLUTION_DIR / filename

    if not proposal_file.exists():
        return f"Error: Proposal '{filename}' not found"

    with open(proposal_file, 'r') as f:
        proposal = json.load(f)

    proposal["status"] = "rejected"
    proposal["rejected_at"] = datetime.now().isoformat()
    proposal["rejection_reason"] = reason

    with open(proposal_file, 'w') as f:
        json.dump(proposal, f, indent=2)

    return f"Identity evolution rejected for {proposal['agent_name']}."


# Tool definitions for agents
IDENTITY_TOOLS = [
    {
        "name": "read_own_identity",
        "description": "Read your current identity file to understand your beliefs, behaviors, and learnings. Use this before proposing any identity evolution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Your agent name (e.g., 'friend', 'archivist', 'profiler')"
                }
            },
            "required": ["agent_name"]
        }
    },
    {
        "name": "read_core_identity",
        "description": "Read the core identity that all agents inherit. Useful for understanding shared beliefs and behaviors.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "propose_identity_evolution",
        "description": "Propose a restructured version of your identity for human approval. Use this to refine beliefs, consolidate learnings, or restructure your identity based on experience. The proposal goes to a review queue - it won't take effect until approved.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Your agent name"
                },
                "new_identity": {
                    "type": "string",
                    "description": "The complete new identity content in markdown format. This replaces your entire identity file, so include all sections."
                },
                "rationale": {
                    "type": "string",
                    "description": "Explain what you're changing and why. What did you learn? What wasn't working? What patterns emerged?"
                },
                "evolution_type": {
                    "type": "string",
                    "enum": ["refinement", "learning", "restructure"],
                    "description": "Type of evolution: 'refinement' (small tweaks), 'learning' (adding insights), 'restructure' (significant reorganization)"
                }
            },
            "required": ["agent_name", "new_identity", "rationale"]
        }
    }
]

# Handlers
IDENTITY_HANDLERS = {
    "read_own_identity": read_own_identity,
    "read_core_identity": read_core_identity,
    "propose_identity_evolution": propose_identity_evolution,
}


# CLI functions for human review
def list_pending():
    """CLI: List pending evolution proposals."""
    print(get_pending_evolutions())


def review(filename: str):
    """CLI: Review a specific proposal."""
    print(review_evolution(filename))


def approve(filename: str):
    """CLI: Approve a proposal."""
    print(approve_evolution(filename))


def reject(filename: str, reason: str = ""):
    """CLI: Reject a proposal."""
    print(reject_evolution(filename, reason))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python identity.py [list|review|approve|reject] [filename] [reason]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        list_pending()
    elif cmd == "review" and len(sys.argv) > 2:
        review(sys.argv[2])
    elif cmd == "approve" and len(sys.argv) > 2:
        approve(sys.argv[2])
    elif cmd == "reject" and len(sys.argv) > 2:
        reason = sys.argv[3] if len(sys.argv) > 3 else ""
        reject(sys.argv[2], reason)
    else:
        print("Unknown command or missing arguments")
