#!/usr/bin/env python3
"""
Migration script: Rename Job → Topic

This script migrates the database schema from jobs to topics:
- Renames table: jobs → topics
- Renames table: job_logs → topic_logs
- Renames column: job_id → topic_id (in topic_logs)
- Recreates indices with new names

Also renames the data directory: data/jobs → data/topics

Run with: python scripts/migrate_jobs_to_topics.py

Before running:
1. Stop the Euno server
2. Create a backup of data/jobs/db.sqlite
"""

import shutil
import sqlite3
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"
OLD_JOBS_DIR = DATA_DIR / "jobs"
NEW_TOPICS_DIR = DATA_DIR / "topics"
DB_PATH = OLD_JOBS_DIR / "db.sqlite"


def migrate_database():
    """Migrate the database schema from jobs to topics."""
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        print("Nothing to migrate.")
        return False

    print(f"Migrating database: {DB_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    try:
        # Check if already migrated
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='topics'"
        )
        if cursor.fetchone():
            print("Database already migrated (topics table exists)")
            return True

        # Check if jobs table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
        )
        if not cursor.fetchone():
            print("No jobs table found - nothing to migrate")
            return True

        print("Starting migration...")

        # Step 1: Rename jobs table to topics
        print("  - Renaming table: jobs → topics")
        conn.execute("ALTER TABLE jobs RENAME TO topics")

        # Step 2: Rename job_logs table to topic_logs
        print("  - Renaming table: job_logs → topic_logs")
        conn.execute("ALTER TABLE job_logs RENAME TO topic_logs")

        # Step 3: Rename column job_id → topic_id in topic_logs
        # SQLite 3.25+ supports ALTER TABLE RENAME COLUMN
        print("  - Renaming column: job_id → topic_id (in topic_logs)")
        conn.execute("ALTER TABLE topic_logs RENAME COLUMN job_id TO topic_id")

        # Step 4: Drop old indices
        print("  - Dropping old indices")
        conn.execute("DROP INDEX IF EXISTS idx_jobs_status")
        conn.execute("DROP INDEX IF EXISTS idx_jobs_parent_id")
        conn.execute("DROP INDEX IF EXISTS idx_jobs_updated_at")
        conn.execute("DROP INDEX IF EXISTS idx_job_logs_job_id")

        # Step 5: Create new indices with updated names
        print("  - Creating new indices")
        conn.execute("CREATE INDEX idx_topics_status ON topics(status)")
        conn.execute("CREATE INDEX idx_topics_parent_id ON topics(parent_id)")
        conn.execute("CREATE INDEX idx_topics_updated_at ON topics(updated_at DESC)")
        conn.execute("CREATE INDEX idx_topic_logs_topic_id ON topic_logs(topic_id)")

        conn.commit()
        print("Database migration complete!")
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def rename_directory():
    """Rename data/jobs → data/topics."""
    if NEW_TOPICS_DIR.exists():
        print(f"Directory already exists: {NEW_TOPICS_DIR}")
        if OLD_JOBS_DIR.exists():
            print(f"WARNING: Both {OLD_JOBS_DIR} and {NEW_TOPICS_DIR} exist!")
            print("Please resolve manually.")
            return False
        return True

    if not OLD_JOBS_DIR.exists():
        print(f"Source directory not found: {OLD_JOBS_DIR}")
        print("Creating empty topics directory...")
        NEW_TOPICS_DIR.mkdir(parents=True, exist_ok=True)
        return True

    print(f"Renaming directory: {OLD_JOBS_DIR} → {NEW_TOPICS_DIR}")
    shutil.move(str(OLD_JOBS_DIR), str(NEW_TOPICS_DIR))
    print("Directory renamed successfully!")
    return True


def main():
    print("=" * 60)
    print("Euno Migration: Job → Topic")
    print("=" * 60)
    print()

    # Step 1: Migrate database (while it's still in data/jobs)
    if not migrate_database():
        print("\nMigration aborted due to database errors.")
        return 1

    print()

    # Step 2: Rename directory
    if not rename_directory():
        print("\nMigration aborted due to directory errors.")
        return 1

    print()
    print("=" * 60)
    print("Migration complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Update your code to use 'topics' instead of 'jobs'")
    print("2. Restart the Euno server")
    return 0


if __name__ == "__main__":
    exit(main())
