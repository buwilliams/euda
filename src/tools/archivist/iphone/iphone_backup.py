#!/usr/bin/env python3
"""
iPhone Backup Extractor
Extracts messages and media from iPhone backups.

Usage:
    python iphone_backup.py                      # Export both messages and media
    python iphone_backup.py --messages           # Export only messages
    python iphone_backup.py --media              # Export only photos/videos
    python iphone_backup.py --backup /path/to    # Use specific backup directory
    python iphone_backup.py --output /path/to    # Custom output directory
"""

import sqlite3
import platform
import re
import shutil
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional
import argparse

# File hashes for iOS backup files
SMS_DB_HASH = '3d0d7e5fb2ce288813306e4d4636395e047a3d28'
ADDRESSBOOK_HASH = '31bb7ba8914766d4ba40d6dfb6113c8b614be442'

# Apple's Core Data epoch offset
APPLE_EPOCH_OFFSET = 978307200


def is_wsl() -> bool:
    """Detect if running under Windows Subsystem for Linux."""
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower()
    except FileNotFoundError:
        return False


def get_windows_username_wsl() -> str | None:
    """Get Windows username when running under WSL."""
    # Scan /mnt/c/Users for real user directories
    users_dir = Path('/mnt/c/Users')
    if users_dir.exists():
        for user_dir in users_dir.iterdir():
            if user_dir.is_dir() and user_dir.name not in ('Public', 'Default', 'Default User', 'All Users'):
                if (user_dir / 'AppData').exists():
                    return user_dir.name
    return None


def get_default_backup_paths() -> list[Path]:
    """Get default backup directory paths based on OS."""
    paths = []
    system = platform.system()

    if system == 'Darwin':
        home = Path.home()
        paths.append(home / 'Library' / 'Application Support' / 'MobileSync' / 'Backup')
    elif system == 'Windows':
        appdata = Path.home() / 'AppData' / 'Roaming'
        paths.append(appdata / 'Apple Computer' / 'MobileSync' / 'Backup')
        paths.append(appdata / 'Apple' / 'MobileSync' / 'Backup')
    elif system == 'Linux':
        if is_wsl():
            username = get_windows_username_wsl()
            if username:
                wsl_userprofile = Path(f'/mnt/c/Users/{username}')
                wsl_appdata = wsl_userprofile / 'AppData' / 'Roaming'
                paths.append(wsl_userprofile / 'Apple' / 'MobileSync' / 'Backup')
                paths.append(wsl_appdata / 'Apple Computer' / 'MobileSync' / 'Backup')
                paths.append(wsl_appdata / 'Apple' / 'MobileSync' / 'Backup')

    return paths


def find_backup_file(backup_dir: Path, file_hash: str) -> Path | None:
    """Find a file by its hash in the backup directory."""
    # Check subdirectory structure (newer backups)
    subdir = backup_dir / file_hash[:2] / file_hash
    if subdir.exists():
        return subdir

    # Check flat structure (older backups)
    flat = backup_dir / file_hash
    if flat.exists():
        return flat

    return None


def find_latest_backup() -> Path | None:
    """Find the most recent iPhone backup."""
    for base_path in get_default_backup_paths():
        if not base_path.exists():
            continue

        backups = []
        for item in base_path.iterdir():
            if item.is_dir():
                manifest = item / 'Manifest.db'
                if manifest.exists():
                    # Check if encrypted
                    manifest_plist = item / 'Manifest.plist'
                    if manifest_plist.exists():
                        try:
                            import plistlib
                            with open(manifest_plist, 'rb') as f:
                                plist = plistlib.load(f)
                                if plist.get('IsEncrypted', False):
                                    continue
                        except Exception:
                            pass
                    backups.append(item)

        if backups:
            # Return most recently modified
            return max(backups, key=lambda p: p.stat().st_mtime)

    return None


def is_backup_encrypted(backup_dir: Path) -> bool:
    """Check if a backup is encrypted."""
    manifest_plist = backup_dir / 'Manifest.plist'
    if manifest_plist.exists():
        try:
            import plistlib
            with open(manifest_plist, 'rb') as f:
                plist = plistlib.load(f)
                return plist.get('IsEncrypted', False)
        except Exception:
            pass
    return False


def normalize_phone(phone: str) -> str:
    """Normalize phone number by removing non-digit characters except leading +."""
    if not phone:
        return ''
    if phone.startswith('+'):
        return '+' + re.sub(r'\D', '', phone[1:])
    return re.sub(r'\D', '', phone)


def extract_contacts(addressbook_path: Path) -> dict[str, str]:
    """Extract phone/email to name mapping from AddressBook database."""
    contacts = {}

    try:
        conn = sqlite3.connect(str(addressbook_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all contacts with their names
        query = """
        SELECT
            p.ROWID,
            p.First as first_name,
            p.Last as last_name,
            p.Organization as organization
        FROM ABPerson p
        """
        cursor.execute(query)
        persons = {row['ROWID']: row for row in cursor.fetchall()}

        # Get phone numbers and emails
        query = """
        SELECT
            record_id,
            value
        FROM ABMultiValue
        WHERE value IS NOT NULL
        """
        cursor.execute(query)

        for row in cursor.fetchall():
            person = persons.get(row['record_id'])
            if not person:
                continue

            # Build name
            first = person['first_name'] or ''
            last = person['last_name'] or ''
            org = person['organization'] or ''

            name = f"{first} {last}".strip()
            if not name:
                name = org

            if name:
                value = row['value']
                # Store both normalized and original
                contacts[value] = name
                normalized = normalize_phone(value)
                if normalized:
                    contacts[normalized] = name

        conn.close()
    except Exception as e:
        print(f"Warning: Could not read contacts: {e}")

    return contacts


def apple_timestamp_to_datetime(timestamp: Optional[int]) -> Optional[str]:
    """Convert Apple Core Data timestamp to ISO 8601 string."""
    if timestamp is None or timestamp == 0:
        return None

    if timestamp > 1_000_000_000_000:
        timestamp = timestamp / 1_000_000_000

    unix_timestamp = timestamp + APPLE_EPOCH_OFFSET
    try:
        dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
        return dt.isoformat()
    except (OSError, OverflowError, ValueError):
        return None


@dataclass
class Message:
    id: int
    guid: str
    text: Optional[str]
    handle: Optional[str]
    service: str
    date: Optional[str]
    date_read: Optional[str]
    date_delivered: Optional[str]
    is_from_me: bool
    is_read: bool
    is_sent: bool
    is_delivered: bool
    chat_id: Optional[int]
    chat_identifier: Optional[str]
    chat_display_name: Optional[str]
    attachments: list


@dataclass
class Attachment:
    id: int
    guid: str
    filename: Optional[str]
    mime_type: Optional[str]
    transfer_name: Optional[str]
    total_bytes: Optional[int]


def extract_messages(db_path: Path) -> list[Message]:
    """Extract all messages from the sms.db database."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    messages_query = """
    SELECT
        m.ROWID as id,
        m.guid,
        m.text,
        m.service,
        m.date,
        m.date_read,
        m.date_delivered,
        m.is_from_me,
        m.is_read,
        m.is_sent,
        m.is_delivered,
        h.id as handle_id,
        h.uncanonicalized_id as handle,
        c.ROWID as chat_id,
        c.chat_identifier,
        c.display_name as chat_display_name
    FROM message m
    LEFT JOIN handle h ON m.handle_id = h.ROWID
    LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
    LEFT JOIN chat c ON cmj.chat_id = c.ROWID
    ORDER BY m.date ASC
    """

    cursor.execute(messages_query)
    rows = cursor.fetchall()

    attachments_query = """
    SELECT
        a.ROWID as id,
        a.guid,
        a.filename,
        a.mime_type,
        a.transfer_name,
        a.total_bytes,
        maj.message_id
    FROM attachment a
    JOIN message_attachment_join maj ON a.ROWID = maj.attachment_id
    """

    cursor.execute(attachments_query)
    attachment_rows = cursor.fetchall()

    attachments_by_message: dict[int, list[Attachment]] = {}
    for row in attachment_rows:
        att = Attachment(
            id=row['id'],
            guid=row['guid'],
            filename=row['filename'],
            mime_type=row['mime_type'],
            transfer_name=row['transfer_name'],
            total_bytes=row['total_bytes']
        )
        message_id = row['message_id']
        if message_id not in attachments_by_message:
            attachments_by_message[message_id] = []
        attachments_by_message[message_id].append(att)

    conn.close()

    messages = []
    for row in rows:
        msg = Message(
            id=row['id'],
            guid=row['guid'],
            text=row['text'],
            handle=row['handle'],
            service=row['service'],
            date=apple_timestamp_to_datetime(row['date']),
            date_read=apple_timestamp_to_datetime(row['date_read']),
            date_delivered=apple_timestamp_to_datetime(row['date_delivered']),
            is_from_me=bool(row['is_from_me']),
            is_read=bool(row['is_read']),
            is_sent=bool(row['is_sent']),
            is_delivered=bool(row['is_delivered']),
            chat_id=row['chat_id'],
            chat_identifier=row['chat_identifier'],
            chat_display_name=row['chat_display_name'],
            attachments=[asdict(a) for a in attachments_by_message.get(row['id'], [])]
        )
        messages.append(msg)

    return messages


def lookup_name(identifier: str, contacts: dict[str, str]) -> str | None:
    """Look up contact name by phone number or email."""
    if not identifier:
        return None

    # Direct lookup
    if identifier in contacts:
        return contacts[identifier]

    # Try normalized phone
    normalized = normalize_phone(identifier)
    if normalized in contacts:
        return contacts[normalized]

    # Try without country code (common case: +1 prefix for US)
    if normalized.startswith('+1') and len(normalized) > 2:
        without_country = normalized[2:]
        if without_country in contacts:
            return contacts[without_country]

    # Try matching last 10 digits
    if len(normalized) >= 10:
        last_10 = normalized[-10:]
        for key, name in contacts.items():
            key_normalized = normalize_phone(key)
            if key_normalized.endswith(last_10):
                return name

    return None


def get_conversation_name(messages: list[Message], contacts: dict[str, str]) -> str:
    """Determine best name for a conversation."""
    # Check for group chat display name
    if messages and messages[0].chat_display_name:
        return messages[0].chat_display_name

    # Collect all participants (excluding self)
    participants = set()
    for msg in messages:
        if not msg.is_from_me and msg.handle:
            name = lookup_name(msg.handle, contacts)
            participants.add(name or msg.handle)

    if not participants:
        # All messages from me, use chat identifier
        if messages and messages[0].chat_identifier:
            ident = messages[0].chat_identifier
            name = lookup_name(ident, contacts)
            return name or ident
        return 'unknown'

    # Single participant
    if len(participants) == 1:
        return list(participants)[0]

    # Multiple participants (group chat without name)
    sorted_participants = sorted(participants)
    if len(sorted_participants) <= 3:
        return ', '.join(sorted_participants)
    return f"{sorted_participants[0]} and {len(sorted_participants) - 1} others"


def format_datetime(iso_date: Optional[str]) -> str:
    """Format ISO datetime for display."""
    if not iso_date:
        return ""
    try:
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return iso_date


def sanitize_filename(name: str) -> str:
    """Create a safe filename from a name."""
    # Replace problematic characters
    safe = re.sub(r'[<>:"/\\|?*]', '_', name)
    safe = re.sub(r'\s+', ' ', safe).strip()
    # Limit length
    if len(safe) > 100:
        safe = safe[:100]
    return safe or 'unknown'


def export_to_markdown(messages: list[Message], output_dir: Path, contacts: dict[str, str]) -> None:
    """Export messages to individual markdown files per conversation."""
    if not messages:
        print("No messages to export")
        return

    # Group messages by conversation
    conversations: dict[str, list[Message]] = {}

    for msg in messages:
        key = msg.chat_identifier or msg.handle or 'unknown'
        if key not in conversations:
            conversations[key] = []
        conversations[key].append(msg)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Track filenames to avoid duplicates
    used_filenames: dict[str, int] = {}

    for conv_id, conv_messages in conversations.items():
        # Get display name for conversation
        conv_name = get_conversation_name(conv_messages, contacts)
        safe_name = sanitize_filename(conv_name)

        # Handle duplicate names
        if safe_name in used_filenames:
            used_filenames[safe_name] += 1
            safe_name = f"{safe_name} ({used_filenames[safe_name]})"
        else:
            used_filenames[safe_name] = 0

        output_path = output_dir / f"{safe_name}.md"

        # Gather metadata
        dates = [m.date for m in conv_messages if m.date]
        services = set(m.service for m in conv_messages if m.service)
        handles = set()
        for m in conv_messages:
            if m.handle:
                name = lookup_name(m.handle, contacts)
                handles.add(name or m.handle)

        sent_count = sum(1 for m in conv_messages if m.is_from_me)
        received_count = len(conv_messages) - sent_count
        attachment_count = sum(1 for m in conv_messages if m.attachments)

        lines = []

        # YAML frontmatter
        lines.append("---")
        lines.append(f"conversation: \"{conv_name}\"")
        if handles:
            lines.append(f"participants: \"{', '.join(sorted(handles))}\"")
        lines.append(f"service: {', '.join(sorted(services))}")
        lines.append(f"message_count: {len(conv_messages)}")
        lines.append(f"sent: {sent_count}")
        lines.append(f"received: {received_count}")
        if attachment_count:
            lines.append(f"attachments: {attachment_count}")
        if dates:
            lines.append(f"first_message: {min(dates)}")
            lines.append(f"last_message: {max(dates)}")
        lines.append("---")
        lines.append("")

        # Title
        lines.append(f"# {conv_name}")
        lines.append("")

        # Messages
        for msg in conv_messages:
            timestamp = format_datetime(msg.date)

            if msg.is_from_me:
                sender = "**Me**"
            else:
                name = lookup_name(msg.handle, contacts) if msg.handle else None
                sender = f"**{name or msg.handle or 'Unknown'}**"

            lines.append(f"### {sender} - {timestamp}")
            lines.append("")

            if msg.text:
                lines.append(msg.text)
            else:
                lines.append("*(no text)*")
            lines.append("")

            if msg.attachments:
                lines.append("**Attachments:**")
                for att in msg.attachments:
                    name = att.get('transfer_name') or att.get('filename') or 'unnamed'
                    mime = att.get('mime_type') or 'unknown type'
                    lines.append(f"- {name} ({mime})")
                lines.append("")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    print(f"Exported {len(conversations)} conversations to {output_dir}")


# Media file extensions to export
MEDIA_EXTENSIONS = {
    '.heic', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
    '.mov', '.mp4', '.m4v', '.avi', '.mkv', '.webm',
    '.mp3', '.m4a', '.wav', '.aac', '.flac',
}


def get_media_files(backup_dir: Path) -> list[tuple[str, str, str]]:
    """Get list of media files from Manifest.db.

    Returns list of (fileID, relativePath, domain) tuples.
    """
    manifest = backup_dir / 'Manifest.db'
    if not manifest.exists():
        return []

    files = []
    conn = sqlite3.connect(str(manifest))
    cursor = conn.cursor()

    # Get files from CameraRollDomain (main photos/videos)
    cursor.execute('''
        SELECT fileID, relativePath, domain
        FROM Files
        WHERE domain = "CameraRollDomain"
        AND relativePath IS NOT NULL
        AND relativePath != ""
        AND flags = 1
    ''')
    files.extend(cursor.fetchall())

    conn.close()

    # Filter to only media files
    media_files = []
    for file_id, rel_path, domain in files:
        ext = Path(rel_path).suffix.lower()
        if ext in MEDIA_EXTENSIONS:
            media_files.append((file_id, rel_path, domain))

    return media_files


def export_media(backup_dir: Path, output_dir: Path) -> None:
    """Export photos and videos from backup to output directory."""
    print("Scanning for media files...")
    media_files = get_media_files(backup_dir)

    if not media_files:
        print("No media files found in backup")
        return

    print(f"Found {len(media_files)} media files")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Count by type
    photos = sum(1 for _, p, _ in media_files if Path(p).suffix.lower() in {'.heic', '.jpg', '.jpeg', '.png', '.gif'})
    videos = sum(1 for _, p, _ in media_files if Path(p).suffix.lower() in {'.mov', '.mp4', '.m4v'})
    print(f"  Photos: {photos}, Videos: {videos}")

    copied = 0
    skipped = 0
    errors = 0

    for file_id, rel_path, domain in media_files:
        # Source file in backup
        src = backup_dir / file_id[:2] / file_id
        if not src.exists():
            # Try flat structure
            src = backup_dir / file_id
            if not src.exists():
                errors += 1
                continue

        # Destination - preserve DCIM structure or use filename
        rel = Path(rel_path)

        # Extract meaningful path (e.g., Media/DCIM/100APPLE/IMG_1234.HEIC)
        parts = rel.parts
        if 'DCIM' in parts:
            dcim_idx = parts.index('DCIM')
            dest_rel = Path(*parts[dcim_idx:])
        else:
            # Just use filename
            dest_rel = Path(rel.name)

        dest = output_dir / dest_rel

        # Skip if already exists and same size
        if dest.exists():
            if dest.stat().st_size == src.stat().st_size:
                skipped += 1
                continue

        # Create parent directory
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Handle duplicate filenames
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            counter = 1
            while dest.exists():
                dest = dest.parent / f"{stem}_{counter}{suffix}"
                counter += 1

        try:
            shutil.copy2(src, dest)
            copied += 1
            if copied % 500 == 0:
                print(f"  Copied {copied} files...")
        except Exception as e:
            errors += 1

    print(f"Media export complete: {copied} copied, {skipped} skipped, {errors} errors")


def main():
    parser = argparse.ArgumentParser(
        description='Extract iPhone messages and media from backup',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--backup', '-b',
        help='Path to iPhone backup directory (auto-detected if not specified)'
    )
    parser.add_argument(
        '--output', '-o',
        default='./output',
        help='Output directory (default: ./output)'
    )
    parser.add_argument(
        '--messages', '-m',
        action='store_true',
        help='Export messages only'
    )
    parser.add_argument(
        '--media',
        action='store_true',
        help='Export photos/videos only'
    )

    args = parser.parse_args()

    # If neither flag specified, do both
    do_messages = args.messages or not args.media
    do_media = args.media or not args.messages
    # But if both specified, do both
    if args.messages and args.media:
        do_messages = True
        do_media = True

    # Find backup
    if args.backup:
        backup_dir = Path(args.backup)
        if not backup_dir.exists():
            print(f"Error: Backup directory not found: {backup_dir}")
            return 1
    else:
        print("Searching for iPhone backup...")
        backup_dir = find_latest_backup()
        if not backup_dir:
            print("Error: No unencrypted iPhone backup found.")
            print("Default search locations:")
            for p in get_default_backup_paths():
                print(f"  {p}")
            print("\nCreate an unencrypted backup via iTunes/Finder, or specify path with --backup")
            return 1

    print(f"Using backup: {backup_dir}")

    # Check encryption
    if is_backup_encrypted(backup_dir):
        print("Error: Backup is encrypted. Create an unencrypted backup to proceed.")
        return 1

    output_dir = Path(args.output)

    # Export messages
    if do_messages:
        sms_db = find_backup_file(backup_dir, SMS_DB_HASH)
        if not sms_db:
            print("Warning: sms.db not found in backup")
        else:
            print(f"Found sms.db: {sms_db}")

            # Find AddressBook (optional)
            contacts = {}
            addressbook = find_backup_file(backup_dir, ADDRESSBOOK_HASH)
            if addressbook:
                print(f"Found AddressBook: {addressbook}")
                contacts = extract_contacts(addressbook)
                print(f"Loaded {len(contacts)} contact entries")
            else:
                print("AddressBook not found, will use phone numbers/emails for names")

            # Extract messages
            print("Extracting messages...")
            messages = extract_messages(sms_db)
            print(f"Found {len(messages)} messages")

            if messages:
                messages_dir = output_dir / 'Messages'
                export_to_markdown(messages, messages_dir, contacts)

                # Stats
                sent = sum(1 for m in messages if m.is_from_me)
                received = len(messages) - sent
                print(f"Messages summary: {sent} sent, {received} received")

                dates = [m.date for m in messages if m.date]
                if dates:
                    print(f"Date range: {min(dates)[:10]} to {max(dates)[:10]}")

    # Export media
    if do_media:
        media_dir = output_dir / 'Photos'
        export_media(backup_dir, media_dir)

    print("\nExport complete!")
    return 0


if __name__ == '__main__':
    exit(main())
