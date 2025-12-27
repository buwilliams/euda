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

Test core files are stored separately in test_core/ (project root) and can be
copied back to inbox/pending/ with --with-test-core flag.

Usage:
    python -m src.tools.admin.fresh_start --help
    python -m src.tools.admin.fresh_start --dry-run
    python -m src.tools.admin.fresh_start --with-test-core
    python -m src.tools.admin.fresh_start --with-test-core --dry-run
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TEST_CORE_DIR = PROJECT_ROOT / "test_core"  # Stored outside data/ to survive fresh-start

# Test core: files that provide meaningful content for synthesis testing
# These are stored in test_core/ at project root, copied to inbox/pending/ when needed
TEST_CORE_FILES = [
    # Personal writings (philosophy essays - reveal thinking patterns)
    "A Primer on Logic.txt",
    "AI Economics - The Time Traveler_s Gift.txt",
    "Cyclic Rationality.txt",
    "Economics in the Intelligence Age.txt",
    "Technohumanism.txt",
    "The Rise of the Outcome Economy.txt",
    "Utility of Truth.txt",
    "Why Hypotheticals Matter.txt",
    # Dated personal notes
    "2024-12-23_meeting.txt",
    "2024-12-24_holiday_note.txt",
    "2024-12-24_idea.txt",
    "2025-12-19_idea.txt",
    "2025-12-24_dev_note.txt",
]

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
    # Synthesis (state includes values, behaviors, epistemic, context, profile, temporal, derived)
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
    Clear contents of a directory, preserving .gitkeep files.

    Returns count of items removed.
    """
    if not dir_path.exists():
        return 0

    count = 0
    for item in dir_path.iterdir():
        if item.name == ".gitkeep":
            continue

        if dry_run:
            print(f"  [DRY-RUN] Would remove: {item}")
        else:
            if item.is_dir():
                shutil.rmtree(item)
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


def copy_test_core_to_pending(dry_run: bool = False) -> int:
    """
    Copy test core files from test_core/ to inbox/pending/ for processing.

    Test core files are stored outside data/ to survive fresh-start.

    Returns count of files copied.
    """
    pending_dir = DATA_DIR / "ingestion" / "state" / "inbox" / "pending"

    if not TEST_CORE_DIR.exists():
        print(f"  Error: Test core directory not found: {TEST_CORE_DIR}")
        print(f"  Please ensure test files exist in {TEST_CORE_DIR}")
        return 0

    if not dry_run:
        pending_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for filename in TEST_CORE_FILES:
        src = TEST_CORE_DIR / filename
        dst = pending_dir / filename

        if not src.exists():
            print(f"  Warning: Test core file not found: {filename}")
            continue

        if dry_run:
            print(f"  [DRY-RUN] Would copy: {filename}")
        else:
            shutil.copy2(src, dst)
        count += 1

    return count


def fresh_start(with_test_core: bool = False, dry_run: bool = False):
    """
    Perform a fresh start of Euno.

    Args:
        with_test_core: If True, copy test core files to pending for reprocessing
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

    # Step 3: Optionally copy test core to pending
    if with_test_core:
        print("\n3. Copying test core for processing...")
        count = copy_test_core_to_pending(dry_run)
        print(f"\n   Test core files copied: {count}")

    # Step 4: Clear ingestion processed hashes (so files can be reprocessed)
    print("\n4. Resetting ingestion tracking...")
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
        if with_test_core:
            print(f"\nTest core ({len(TEST_CORE_FILES)} files) ready in inbox/pending/")
            print("Run the ingestion agent to process them.")
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
    parser.add_argument(
        "--with-test-core",
        action="store_true",
        help="Copy test core files from test_core/ to inbox/pending/ for processing"
    )
    parser.add_argument(
        "--list-test-core",
        action="store_true",
        help="List test core files and exit"
    )

    args = parser.parse_args()

    if args.list_test_core:
        print(f"Test Core Location: {TEST_CORE_DIR}")
        print(f"Test Core Files ({len(TEST_CORE_FILES)} total):")
        for f in TEST_CORE_FILES:
            path = TEST_CORE_DIR / f
            status = "✓" if path.exists() else "✗ MISSING"
            print(f"  {status} {f}")
        return

    fresh_start(with_test_core=args.with_test_core, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
