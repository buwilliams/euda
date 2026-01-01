"""
Fresh Start utility for Euno.

Moves the current data/ directory to data_backup-[num]/ and creates a
completely fresh data/ directory with minimal structure.

The new data/ directory contains:
- Directory structure with .gitkeep files for git tracking
- NO user data (lifelog, conversations, tasks, etc.)
- NO configuration (agent personas are in git-tracked locations)

Backups are stored as data_backup-1/, data_backup-2/, etc. and are gitignored.

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

# Complete directory structure for fresh data/
# Each path gets created with a .gitkeep file
DIRECTORY_STRUCTURE = [
    # Shared (agent personas moved to src/agents/personas)
    "shared/state/lifelog",
    "shared/state/signals",
    "shared/state/notifications",
    "shared/state/profile",
    "shared/state/auth",
    "shared/state/evolution",
    "shared/config",
    "shared/logs",

    # Archivist
    "archivist/state/inbox/pending",
    "archivist/state/inbox/processing",
    "archivist/state/inbox/processed",
    "archivist/state/inbox/failed",
    "archivist/state/inbox/deferred",
    "archivist/state/digests",
    "archivist/config",
    "archivist/logs",

    # Profiler
    "profiler/state",
    "profiler/config",
    "profiler/logs",

    # Curator
    "curator/state/queue",
    "curator/config",
    "curator/logs",

    # Friend
    "friend/state/conversations/sessions",
    "friend/state/conversations/daily",
    "friend/state/cards/received",
    "friend/config",
    "friend/logs",

    # Worker
    "worker/state/tasks",
    "worker/state/projects",
    "worker/state/actions",
    "worker/state/archive",
    "worker/config",
    "worker/logs",

    # Adaptor
    "adaptor/state/output",
    "adaptor/config",
    "adaptor/logs",
]

# Files to copy from backup to new data/ (essential config that lives in data/)
# Note: Agent personas moved to src/agents/personas/ (part of codebase)
# Note: Profile contracts moved to src/agents/contracts/ (part of codebase)
FILES_TO_RESTORE = [
    # Currently empty - all config files are now in src/
]


def get_next_backup_number() -> int:
    """Find the next available backup number."""
    n = 1
    while (PROJECT_ROOT / f"data_backup-{n}").exists():
        n += 1
    return n


def create_directory_with_gitkeep(dir_path: Path, dry_run: bool = False):
    """Create directory and add .gitkeep file."""
    if dry_run:
        print(f"  [DRY-RUN] Would create: {dir_path}")
        return

    dir_path.mkdir(parents=True, exist_ok=True)
    gitkeep = dir_path / ".gitkeep"
    gitkeep.touch()


def fresh_start(dry_run: bool = False):
    """
    Perform a fresh start of Euno.

    1. Move data/ to data_backup-[num]/
    2. Create fresh data/ directory structure
    3. Restore essential git-tracked files from backup

    Args:
        dry_run: If True, only show what would be done
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 60)
    print(f"Euno Fresh Start {'(DRY RUN)' if dry_run else ''}")
    print(f"Time: {timestamp}")
    print("=" * 60)

    # Step 1: Move current data/ to backup
    backup_num = get_next_backup_number()
    backup_dir = PROJECT_ROOT / f"data_backup-{backup_num}"

    print(f"\n1. Backing up data/ to data_backup-{backup_num}/...")

    if DATA_DIR.exists():
        if dry_run:
            print(f"   [DRY-RUN] Would move: data/ -> data_backup-{backup_num}/")
        else:
            shutil.move(str(DATA_DIR), str(backup_dir))
            print(f"   ✓ Moved to data_backup-{backup_num}/")
    else:
        print("   (no existing data/ directory)")
        backup_dir = None

    # Step 2: Create fresh directory structure
    print("\n2. Creating fresh data/ directory structure...")

    for rel_path in DIRECTORY_STRUCTURE:
        dir_path = DATA_DIR / rel_path
        create_directory_with_gitkeep(dir_path, dry_run)

    if not dry_run:
        # Also add .gitkeep to root directories
        (DATA_DIR / ".gitkeep").touch()
        print(f"   ✓ Created {len(DIRECTORY_STRUCTURE)} directories with .gitkeep files")

    # Step 3: Restore essential git-tracked files from backup
    print("\n3. Restoring essential config files...")

    restored_count = 0
    for rel_path in FILES_TO_RESTORE:
        if backup_dir:
            src = backup_dir / rel_path
            dst = DATA_DIR / rel_path

            if src.exists():
                if dry_run:
                    print(f"   [DRY-RUN] Would restore: {rel_path}")
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(src), str(dst))
                    restored_count += 1

    if not dry_run:
        print(f"   ✓ Restored {restored_count} files")

    # Summary
    print("\n" + "=" * 60)
    if dry_run:
        print("DRY RUN complete. No changes were made.")
    else:
        print("Fresh start complete!")
        print(f"\nBackup location: data_backup-{backup_num}/")
        print("New data/ directory is clean and ready.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Fresh start Euno - backup data/ and create clean directory"
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
