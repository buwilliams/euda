"""
Memory Sync Handler - Agent memory synchronization.

Handles sync of:
- Short-term memory (JSONL files): Merge by entry ID (union of entries)
- Long-term memory (Markdown files): Append new sections with instance markers

Strategy for short-term memory:
- Entries have unique IDs (mem-XXXXXXXX)
- Union of all entries from both sides
- If same ID exists with different content, keep the one with later date_mentioned

Strategy for long-term memory:
- Daily markdown files with timestamped sections
- Append new sections from remote that don't exist locally
- Use instance markers to track origin
"""

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional

from .base import SyncHandler
from ..sync import SyncChange
from ..transport import Transport
from ..conflicts import Conflict, ConflictType, create_conflict
from ..state import get_instance_id


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


class MemorySyncHandler(SyncHandler):
    """Handler for agent memory sync."""

    @property
    def name(self) -> str:
        return "memory"

    def detect_changes(
        self,
        transport: Transport,
        direction: str,
    ) -> Tuple[List[SyncChange], List[Conflict]]:
        """Detect memory changes between local and remote."""
        changes: List[SyncChange] = []
        conflicts: List[Conflict] = []

        # Get list of all agents (local and remote)
        local_agents = self._get_local_agents()
        remote_agents = self._get_remote_agents(transport)
        all_agents = local_agents | remote_agents

        for agent_id in all_agents:
            # Check short-term memory
            st_changes, st_conflicts = self._check_short_term(transport, agent_id, direction)
            changes.extend(st_changes)
            conflicts.extend(st_conflicts)

            # Check long-term memory
            lt_changes, lt_conflicts = self._check_long_term(transport, agent_id, direction)
            changes.extend(lt_changes)
            conflicts.extend(lt_conflicts)

        return changes, conflicts

    def apply_changes(
        self,
        transport: Transport,
        direction: str,
        changes: List[SyncChange],
    ) -> None:
        """Apply memory changes."""
        for change in changes:
            if change.handler != self.name:
                continue
            if change.type == "conflict":
                continue

            try:
                item_id = change.item_id
                # Parse item_id format: "agent_id:memory_type:details"
                parts = item_id.split(":", 2)
                agent_id = parts[0]
                memory_type = parts[1] if len(parts) > 1 else ""

                if memory_type == "short-term":
                    if change.type == "push":
                        self._push_short_term(transport, agent_id)
                    else:
                        self._pull_short_term(transport, agent_id)
                elif memory_type == "long-term":
                    file_path = parts[2] if len(parts) > 2 else ""
                    if change.type == "push":
                        self._push_long_term_file(transport, agent_id, file_path)
                    else:
                        self._pull_long_term_file(transport, agent_id, file_path)

                change.applied = True
            except Exception as e:
                change.error = str(e)

    def _get_local_agents(self) -> Set[str]:
        """Get set of local agent IDs with memory."""
        agents = set()
        if AGENTS_DIR.exists():
            for agent_dir in AGENTS_DIR.iterdir():
                if agent_dir.is_dir():
                    memory_dir = agent_dir / "memory"
                    if memory_dir.exists():
                        agents.add(agent_dir.name)
        return agents

    def _get_remote_agents(self, transport: Transport) -> Set[str]:
        """Get set of remote agent IDs with memory."""
        agents = set()
        remote_agents = transport.list_remote_files("agents")
        for agent_id in remote_agents:
            if transport.remote_directory_exists(f"agents/{agent_id}/memory"):
                agents.add(agent_id)
        return agents

    def _check_short_term(
        self,
        transport: Transport,
        agent_id: str,
        direction: str,
    ) -> Tuple[List[SyncChange], List[Conflict]]:
        """Check short-term memory for an agent."""
        changes: List[SyncChange] = []
        conflicts: List[Conflict] = []

        local_path = AGENTS_DIR / agent_id / "memory" / "short-term.jsonl"
        remote_path = f"agents/{agent_id}/memory/short-term.jsonl"

        local_exists = local_path.exists()
        remote_exists = transport.remote_file_exists(remote_path)

        if not local_exists and not remote_exists:
            return changes, conflicts

        # Load local entries
        local_entries = {}
        if local_exists:
            with open(local_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            local_entries[entry["id"]] = entry
                        except (json.JSONDecodeError, KeyError):
                            continue

        # Load remote entries
        remote_entries = {}
        if remote_exists:
            content = transport.get_remote_file_content(remote_path)
            if content:
                for line in content.split("\n"):
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            remote_entries[entry["id"]] = entry
                        except (json.JSONDecodeError, KeyError):
                            continue

        # Find differences
        local_only = set(local_entries.keys()) - set(remote_entries.keys())
        remote_only = set(remote_entries.keys()) - set(local_entries.keys())
        both = set(local_entries.keys()) & set(remote_entries.keys())

        # Check for modified entries (same ID, different content)
        modified = set()
        for entry_id in both:
            local = local_entries[entry_id]
            remote = remote_entries[entry_id]
            if local != remote:
                modified.add(entry_id)

        if local_only and direction in ("push", "bidirectional"):
            changes.append(SyncChange(
                type="push",
                handler=self.name,
                item_id=f"{agent_id}:short-term",
                description=f"Push {len(local_only)} short-term memory entries for {agent_id}",
            ))

        if remote_only and direction in ("pull", "bidirectional"):
            changes.append(SyncChange(
                type="pull",
                handler=self.name,
                item_id=f"{agent_id}:short-term",
                description=f"Pull {len(remote_only)} short-term memory entries for {agent_id}",
            ))

        if modified:
            # For modified entries, we need to merge or conflict
            # Use date_mentioned to decide which is newer
            for entry_id in modified:
                local = local_entries[entry_id]
                remote = remote_entries[entry_id]
                local_date = local.get("date_mentioned", "")
                remote_date = remote.get("date_mentioned", "")

                if local_date > remote_date:
                    if direction in ("push", "bidirectional"):
                        # Local is newer, already counted in push
                        pass
                elif remote_date > local_date:
                    if direction in ("pull", "bidirectional"):
                        # Remote is newer, already counted in pull
                        pass
                else:
                    # Same date but different content - conflict
                    conflicts.append(create_conflict(
                        conflict_type=ConflictType.MEMORY_SHORT_TERM,
                        item_id=f"{agent_id}:{entry_id}",
                        description=f"Short-term memory entry modified on both sides: {entry_id}",
                        local=local,
                        remote=remote,
                        local_timestamp=local_date,
                        remote_timestamp=remote_date,
                    ))

        return changes, conflicts

    def _check_long_term(
        self,
        transport: Transport,
        agent_id: str,
        direction: str,
    ) -> Tuple[List[SyncChange], List[Conflict]]:
        """Check long-term memory for an agent."""
        changes: List[SyncChange] = []
        conflicts: List[Conflict] = []

        local_base = AGENTS_DIR / agent_id / "memory" / "long-term"
        remote_base = f"agents/{agent_id}/memory/long-term"

        # Get local files (organized by year)
        local_files = set()
        if local_base.exists():
            for year_dir in local_base.iterdir():
                if year_dir.is_dir() and year_dir.name.isdigit():
                    for f in year_dir.glob("*.md"):
                        local_files.add(f"{year_dir.name}/{f.name}")

        # Get remote files
        remote_files = set()
        if transport.remote_directory_exists(remote_base):
            years = transport.list_remote_files(remote_base)
            for year in years:
                if year.isdigit():
                    files = transport.list_remote_files(f"{remote_base}/{year}")
                    for f in files:
                        if f.endswith(".md"):
                            remote_files.add(f"{year}/{f}")

        # Files only on local
        local_only = local_files - remote_files
        if local_only and direction in ("push", "bidirectional"):
            for f in local_only:
                changes.append(SyncChange(
                    type="push",
                    handler=self.name,
                    item_id=f"{agent_id}:long-term:{f}",
                    description=f"Push long-term memory: {agent_id}/{f}",
                ))

        # Files only on remote
        remote_only = remote_files - local_files
        if remote_only and direction in ("pull", "bidirectional"):
            for f in remote_only:
                changes.append(SyncChange(
                    type="pull",
                    handler=self.name,
                    item_id=f"{agent_id}:long-term:{f}",
                    description=f"Pull long-term memory: {agent_id}/{f}",
                ))

        # Files on both - check for differences (append-only merge)
        common_files = local_files & remote_files
        for f in common_files:
            result = self._check_long_term_file(transport, agent_id, f, direction)
            if result:
                if isinstance(result, list):
                    changes.extend(result)
                elif isinstance(result, Conflict):
                    conflicts.append(result)

        return changes, conflicts

    def _check_long_term_file(
        self,
        transport: Transport,
        agent_id: str,
        file_path: str,
        direction: str,
    ) -> Optional[List[SyncChange] | Conflict]:
        """Check a single long-term memory file.

        Long-term memory uses append-only strategy:
        - Each section starts with "## <time> · <source>"
        - Sections from remote not in local should be pulled
        - Sections from local not in remote should be pushed
        """
        local_path = AGENTS_DIR / agent_id / "memory" / "long-term" / file_path
        remote_rel = f"agents/{agent_id}/memory/long-term/{file_path}"

        # Read local content
        local_content = ""
        if local_path.exists():
            local_content = local_path.read_text()

        # Read remote content
        remote_content = transport.get_remote_file_content(remote_rel) or ""

        if local_content == remote_content:
            return None

        # Parse sections from each
        local_sections = self._parse_lt_sections(local_content)
        remote_sections = self._parse_lt_sections(remote_content)

        local_keys = set(local_sections.keys())
        remote_keys = set(remote_sections.keys())

        changes = []

        # Sections to push
        push_sections = local_keys - remote_keys
        if push_sections and direction in ("push", "bidirectional"):
            changes.append(SyncChange(
                type="push",
                handler=self.name,
                item_id=f"{agent_id}:long-term:{file_path}",
                description=f"Push {len(push_sections)} sections to {file_path}",
            ))

        # Sections to pull
        pull_sections = remote_keys - local_keys
        if pull_sections and direction in ("pull", "bidirectional"):
            changes.append(SyncChange(
                type="pull",
                handler=self.name,
                item_id=f"{agent_id}:long-term:{file_path}",
                description=f"Pull {len(pull_sections)} sections from {file_path}",
            ))

        return changes if changes else None

    def _parse_lt_sections(self, content: str) -> Dict[str, str]:
        """Parse long-term memory file into sections.

        Returns dict mapping section header to full section content.
        """
        sections = {}
        current_header = None
        current_content = []

        for line in content.split("\n"):
            if line.startswith("## "):
                # Save previous section
                if current_header:
                    sections[current_header] = "\n".join(current_content)

                current_header = line
                current_content = [line]
            elif current_header:
                current_content.append(line)

        # Save last section
        if current_header:
            sections[current_header] = "\n".join(current_content)

        return sections

    def _push_short_term(self, transport: Transport, agent_id: str):
        """Push short-term memory to remote (merge)."""
        local_path = AGENTS_DIR / agent_id / "memory" / "short-term.jsonl"
        remote_path = f"agents/{agent_id}/memory/short-term.jsonl"

        if not local_path.exists():
            return

        # Load both
        local_entries = {}
        with open(local_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        local_entries[entry["id"]] = entry
                    except (json.JSONDecodeError, KeyError):
                        continue

        remote_entries = {}
        remote_content = transport.get_remote_file_content(remote_path)
        if remote_content:
            for line in remote_content.split("\n"):
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        remote_entries[entry["id"]] = entry
                    except (json.JSONDecodeError, KeyError):
                        continue

        # Merge (local wins for conflicts by date)
        merged = dict(remote_entries)
        for entry_id, entry in local_entries.items():
            if entry_id in merged:
                local_date = entry.get("date_mentioned", "")
                remote_date = merged[entry_id].get("date_mentioned", "")
                if local_date >= remote_date:
                    merged[entry_id] = entry
            else:
                merged[entry_id] = entry

        # Write merged content to temp and push
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for entry in merged.values():
                f.write(json.dumps(entry) + "\n")
            temp_path = Path(f.name)

        try:
            transport.push_file(temp_path, remote_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def _pull_short_term(self, transport: Transport, agent_id: str):
        """Pull short-term memory from remote (merge)."""
        local_path = AGENTS_DIR / agent_id / "memory" / "short-term.jsonl"
        remote_path = f"agents/{agent_id}/memory/short-term.jsonl"

        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Load both
        local_entries = {}
        if local_path.exists():
            with open(local_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            local_entries[entry["id"]] = entry
                        except (json.JSONDecodeError, KeyError):
                            continue

        remote_entries = {}
        remote_content = transport.get_remote_file_content(remote_path)
        if remote_content:
            for line in remote_content.split("\n"):
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        remote_entries[entry["id"]] = entry
                    except (json.JSONDecodeError, KeyError):
                        continue

        # Merge (remote wins for new entries, local wins for conflicts)
        merged = dict(local_entries)
        for entry_id, entry in remote_entries.items():
            if entry_id not in merged:
                merged[entry_id] = entry
            else:
                # Keep newer by date
                local_date = merged[entry_id].get("date_mentioned", "")
                remote_date = entry.get("date_mentioned", "")
                if remote_date > local_date:
                    merged[entry_id] = entry

        # Write merged
        with open(local_path, 'w') as f:
            for entry in merged.values():
                f.write(json.dumps(entry) + "\n")

    def _push_long_term_file(self, transport: Transport, agent_id: str, file_path: str):
        """Push long-term memory file to remote (append-only merge)."""
        local_full = AGENTS_DIR / agent_id / "memory" / "long-term" / file_path
        remote_rel = f"agents/{agent_id}/memory/long-term/{file_path}"

        if not local_full.exists():
            return

        local_content = local_full.read_text()
        remote_content = transport.get_remote_file_content(remote_rel) or ""

        # Parse sections
        local_sections = self._parse_lt_sections(local_content)
        remote_sections = self._parse_lt_sections(remote_content)

        # Merge (append local-only sections to remote)
        merged = dict(remote_sections)
        for header, content in local_sections.items():
            if header not in merged:
                merged[header] = content

        # Reconstruct file preserving order
        all_headers = list(remote_sections.keys())
        for header in local_sections.keys():
            if header not in all_headers:
                all_headers.append(header)

        # Sort headers by time
        all_headers.sort()

        # Build merged content
        lines = []
        # Check if there's a title line
        for line in (remote_content or local_content).split("\n"):
            if line.startswith("# "):
                lines.append(line)
                lines.append("")
                break

        for header in all_headers:
            if header in merged:
                lines.append(merged[header])
                lines.append("")

        merged_content = "\n".join(lines).rstrip() + "\n"

        # Write to temp and push
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(merged_content)
            temp_path = Path(f.name)

        try:
            transport.push_file(temp_path, remote_rel)
        finally:
            temp_path.unlink(missing_ok=True)

    def _pull_long_term_file(self, transport: Transport, agent_id: str, file_path: str):
        """Pull long-term memory file from remote (append-only merge)."""
        local_full = AGENTS_DIR / agent_id / "memory" / "long-term" / file_path
        remote_rel = f"agents/{agent_id}/memory/long-term/{file_path}"

        local_full.parent.mkdir(parents=True, exist_ok=True)

        local_content = local_full.read_text() if local_full.exists() else ""
        remote_content = transport.get_remote_file_content(remote_rel) or ""

        # Parse sections
        local_sections = self._parse_lt_sections(local_content)
        remote_sections = self._parse_lt_sections(remote_content)

        # Merge (append remote-only sections to local)
        merged = dict(local_sections)
        for header, content in remote_sections.items():
            if header not in merged:
                merged[header] = content

        # Reconstruct file preserving order
        all_headers = list(local_sections.keys())
        for header in remote_sections.keys():
            if header not in all_headers:
                all_headers.append(header)

        # Sort headers by time
        all_headers.sort()

        # Build merged content
        lines = []
        # Check if there's a title line
        for line in (local_content or remote_content).split("\n"):
            if line.startswith("# "):
                lines.append(line)
                lines.append("")
                break

        for header in all_headers:
            if header in merged:
                lines.append(merged[header])
                lines.append("")

        merged_content = "\n".join(lines).rstrip() + "\n"

        # Write
        local_full.write_text(merged_content)
