"""
Fresh Start utility for Euno.

Clears ALL generated data and user content while preserving only:
- System configuration (agent identities, profile contract, LLM config)
- Prompts (ingestion, synthesis, attention, worker, evolution)

Everything else is wiped clean, including:
- Inbox (processed, pending, failed, deferred)
- Lifelogs, signals, notifications
- All synthesis data (values, behaviors, epistemic, context)
- All agent state and conversation history
- Tasks, projects, opportunities
- User profile preferences

Usage:
    python -m src.tools.admin.fresh_start --help
    python -m src.tools.admin.fresh_start --dry-run
    python -m src.tools.admin.fresh_start
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Directories to PRESERVE (not cleared) - only system config, not user data
PRESERVE_DIRS = [
    # Shared system config
    "shared/state/identity",     # Agent identity files
    "shared/state/profile",      # Profile contract and policy
    "shared/config",             # LLM config
    # Agent prompts (all agents)
    "ingestion/prompts",
    "summary/prompts",
    "synthesis/prompts",
    "world/prompts",
    "attention/prompts",
    "interaction/prompts",
    "worker/prompts",
    "evolution/prompts",
]

# Directories to CLEAR (remove contents but keep .gitkeep)
# Standard pattern: each agent has config/, logs/, prompts/, state/
# We clear state/ and logs/, preserve config/ and prompts/
CLEAR_DIRS = [
    # Shared state (lifelog, signals, notifications, evolution proposals)
    "shared/state/lifelog",
    "shared/state/signals",
    "shared/state/notifications",
    "shared/state/evolution",
    "shared/logs",
    # Ingestion (state includes inbox, digests, queue.json)
    "ingestion/state",
    "ingestion/config",              # Processed hashes, etc.
    "ingestion/logs",
    # Summary
    "summary/state",
    "summary/logs",
    # Synthesis (state includes values, behaviors, epistemic, context, profile)
    "synthesis/state",
    "synthesis/logs",
    # World (state includes opportunities)
    "world/state",
    "world/logs",
    # Attention (state includes queue)
    "attention/state",
    "attention/logs",
    # Interaction (state includes conversations, cards)
    "interaction/state",
    "interaction/logs",
    # Worker (state includes tasks, projects, actions, archive)
    "worker/state",
    "worker/logs",
    # Evolution (state includes output)
    "evolution/state",
    "evolution/logs",
]


def clear_directory(dir_path: Path, dry_run: bool = False) -> int:
    """
    Clear contents of a directory, preserving .gitkeep files and directory structure.

    Returns count of items removed.
    """
    if not dir_path.exists():
        return 0

    count = 0
    for item in dir_path.iterdir():
        if item.name == ".gitkeep":
            continue

        if item.is_dir():
            # Recursively clear subdirectory, preserving structure
            count += clear_directory(item, dry_run)
        else:
            if dry_run:
                print(f"  [DRY-RUN] Would remove: {item}")
            else:
                item.unlink()
            count += 1

    return count


def ensure_gitkeep(dir_path: Path, dry_run: bool = False):
    """Ensure directory exists and has a .gitkeep file."""
    if dry_run:
        if not dir_path.exists():
            print(f"  [DRY-RUN] Would create: {dir_path}")
        return

    dir_path.mkdir(parents=True, exist_ok=True)
    gitkeep = dir_path / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()


def fresh_start(dry_run: bool = False):
    """
    Perform a fresh start of Euno.

    Args:
        dry_run: If True, only show what would be done
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 60)
    print(f"Euno Fresh Start {'(DRY RUN)' if dry_run else ''}")
    print(f"Time: {timestamp}")
    print("=" * 60)

    # Step 1: Clear generated data
    print("\n1. Clearing generated data...")
    total_cleared = 0

    for rel_path in CLEAR_DIRS:
        dir_path = DATA_DIR / rel_path
        count = clear_directory(dir_path, dry_run)
        if count > 0:
            print(f"   {rel_path}: {count} items")
            total_cleared += count

        # Ensure directory and .gitkeep exist
        ensure_gitkeep(dir_path, dry_run)

    print(f"\n   Total cleared: {total_cleared} items")

    # Step 2: Ensure preserved directories exist
    print("\n2. Preserving system directories...")
    for rel_path in PRESERVE_DIRS:
        dir_path = DATA_DIR / rel_path
        ensure_gitkeep(dir_path, dry_run)
        if not dry_run:
            print(f"   ✓ {rel_path}")

    # Step 3: Clear ingestion processed hashes (so files can be reprocessed)
    print("\n3. Resetting ingestion tracking...")
    config_dir = DATA_DIR / "ingestion" / "config"
    hashes_file = config_dir / "processed_hashes.json"
    if hashes_file.exists():
        if dry_run:
            print(f"   [DRY-RUN] Would remove: processed_hashes.json")
        else:
            hashes_file.unlink()
            print("   ✓ Cleared processed_hashes.json")

    state_file = DATA_DIR / "ingestion" / "state" / "state.json"
    if state_file.exists():
        if dry_run:
            print(f"   [DRY-RUN] Would remove: state.json")
        else:
            state_file.unlink()
            print("   ✓ Cleared ingestion state")

    print("\n" + "=" * 60)
    if dry_run:
        print("DRY RUN complete. No changes were made.")
    else:
        print("Fresh start complete!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Fresh start Euno - clear generated data while preserving system config"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()
    fresh_start(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
