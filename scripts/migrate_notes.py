#!/usr/bin/env python3
"""
Migrate notes from flat file format to individual files.

Old format: data/worker/state/projects/notes/{project_id}.md
    - All notes concatenated, separated by ---
    - Headers: ## YYYY-MM-DD HH:MM - Type: Title

New format: data/worker/state/projects/notes/{project_id}/YYYYMMDD-HHMMSS.md
    - Each note as separate file
    - YAML frontmatter with date, type, title
"""

import re
from pathlib import Path
from datetime import datetime

NOTES_DIR = Path(__file__).parent.parent / "data" / "worker" / "state" / "projects" / "notes"


def parse_old_notes(content: str) -> list:
    """Parse old flat file format into note entries."""
    raw_notes = re.split(r'\n+---\n+', content)
    notes = []

    for raw_note in raw_notes:
        raw_note = raw_note.strip()
        if not raw_note:
            continue

        # Parse header: ## YYYY-MM-DD HH:MM - Type: Title
        header_match = re.match(r'^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) - (?:(\w+): )?(.+)', raw_note)
        if header_match:
            date_str = header_match.group(1)
            note_type = header_match.group(2) or "Note"
            title = header_match.group(3)
            content_start = raw_note.find('\n')
            body = raw_note[content_start:].strip() if content_start > 0 else ""
        else:
            # Fallback
            lines = raw_note.split('\n', 1)
            title = lines[0].lstrip('# ')
            body = lines[1].strip() if len(lines) > 1 else ""
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            note_type = "Note"

        notes.append({
            "date": date_str,
            "type": note_type,
            "title": title,
            "content": body
        })

    return notes


def migrate_project_notes(old_file: Path):
    """Migrate a single project's notes to new format."""
    project_id = old_file.stem
    print(f"Migrating {project_id}...")

    content = old_file.read_text()
    notes = parse_old_notes(content)

    if not notes:
        print(f"  No notes found, skipping")
        return

    # Create new directory
    new_dir = NOTES_DIR / project_id
    new_dir.mkdir(parents=True, exist_ok=True)

    # Write each note as individual file
    for i, note in enumerate(notes):
        # Generate unique filename from date
        try:
            dt = datetime.strptime(note["date"], "%Y-%m-%d %H:%M")
            # Add index to prevent collisions for same-minute notes
            filename = dt.strftime(f"%Y%m%d-%H%M{i:02d}.md")
        except:
            filename = f"migrated-{i:04d}.md"

        # Format with YAML frontmatter
        note_content = f"""---
date: {note["date"]}
type: {note["type"]}
title: {note["title"]}
---

{note["content"]}
"""

        note_file = new_dir / filename
        note_file.write_text(note_content)
        print(f"  Created {filename}")

    # Rename old file as backup
    backup_file = old_file.with_suffix('.md.bak')
    old_file.rename(backup_file)
    print(f"  Backed up old file to {backup_file.name}")


def main():
    """Migrate all project notes."""
    print("Migrating notes to new format...\n")

    # Find all old-format note files (direct .md files, not directories)
    old_files = [f for f in NOTES_DIR.glob("*.md") if f.is_file()]

    if not old_files:
        print("No old-format notes found.")
        return

    print(f"Found {len(old_files)} project(s) with notes to migrate\n")

    for old_file in old_files:
        migrate_project_notes(old_file)
        print()

    print("Migration complete!")


if __name__ == "__main__":
    main()
