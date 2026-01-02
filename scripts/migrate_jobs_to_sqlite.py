#!/usr/bin/env python3
"""
Migration script: JSON files -> SQLite database

Usage:
    python scripts/migrate_jobs_to_sqlite.py [--dry-run]

This script:
1. Creates the SQLite database if it doesn't exist
2. Reads all existing JSON job files
3. Inserts them into the database
4. Backs up and removes JSON files
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
JOBS_DIR = DATA_DIR / "jobs"
DB_PATH = JOBS_DIR / "db.sqlite"


def create_schema(conn: sqlite3.Connection):
    """Create database schema."""
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            parent_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'completed', 'archived')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            created_by TEXT NOT NULL DEFAULT 'user',
            description TEXT,
            due_date TEXT,
            someday INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            tags TEXT
        );

        CREATE TABLE IF NOT EXISTS job_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            timestamp TEXT NOT NULL,
            agent TEXT NOT NULL,
            action TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_parent_id ON jobs(parent_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_updated_at ON jobs(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_job_logs_job_id ON job_logs(job_id);
    ''')
    conn.commit()


def migrate_job(conn: sqlite3.Connection, job_file: Path) -> bool:
    """Migrate a single job file to the database."""
    try:
        with open(job_file) as f:
            job = json.load(f)

        # Check if already migrated
        cursor = conn.execute("SELECT id FROM jobs WHERE id = ?", (job["id"],))
        if cursor.fetchone():
            print(f"  Skipping {job['id']} (already exists)")
            return False

        # Insert job
        conn.execute('''
            INSERT INTO jobs (id, name, parent_id, status, created_at, updated_at,
                            created_by, description, due_date, someday, completed_at, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job["id"],
            job["name"],
            job.get("parent_id"),
            job.get("status", "todo"),
            job["created_at"],
            job["updated_at"],
            job.get("created_by", "user"),
            job.get("description"),
            job.get("due_date"),
            int(job.get("someday", False)),
            job.get("completed_at"),
            json.dumps(job.get("tags", []))
        ))

        # Insert logs
        for log_entry in job.get("log", []):
            conn.execute('''
                INSERT INTO job_logs (job_id, timestamp, agent, action)
                VALUES (?, ?, ?, ?)
            ''', (
                job["id"],
                log_entry["timestamp"],
                log_entry["agent"],
                log_entry["action"]
            ))

        print(f"  Migrated {job['id']}: {job['name']}")
        return True

    except Exception as e:
        print(f"  ERROR migrating {job_file}: {e}")
        return False


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("Euno Jobs Migration: JSON -> SQLite")
    print("=" * 60)

    if dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")

    # Ensure jobs directory exists
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    # Find JSON files
    json_files = list(JOBS_DIR.glob("*.json"))
    print(f"\nFound {len(json_files)} JSON job files")

    if not json_files:
        print("Nothing to migrate.")
        if not dry_run:
            # Still create the database schema for fresh installs
            print(f"\nCreating empty database at {DB_PATH}")
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("PRAGMA foreign_keys = ON")
            create_schema(conn)
            conn.close()
            print("Database created successfully.")
        return

    if dry_run:
        print("\nWould migrate:")
        for f in json_files:
            print(f"  - {f.name}")
        return

    # Create database
    print(f"\nCreating database at {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    create_schema(conn)

    # Migrate jobs
    print("\nMigrating jobs:")
    migrated = 0
    for job_file in json_files:
        if migrate_job(conn, job_file):
            migrated += 1

    conn.commit()

    # Verify migration
    cursor = conn.execute("SELECT COUNT(*) FROM jobs")
    db_count = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(*) FROM job_logs")
    log_count = cursor.fetchone()[0]

    print(f"\nMigration complete:")
    print(f"  - Jobs in database: {db_count}")
    print(f"  - Log entries: {log_count}")
    print(f"  - Newly migrated: {migrated}")

    conn.close()

    # Create backup and remove JSON files
    if migrated > 0:
        backup_dir = DATA_DIR / f"jobs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"\nBacking up JSON files to {backup_dir}")
        backup_dir.mkdir(exist_ok=True)

        for job_file in json_files:
            job_file.rename(backup_dir / job_file.name)

        print(f"Moved {len(json_files)} JSON files to backup")

    print("\n" + "=" * 60)
    print("Migration successful!")
    print("=" * 60)


if __name__ == "__main__":
    main()
