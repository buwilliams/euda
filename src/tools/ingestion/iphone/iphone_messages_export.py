#!/usr/bin/env python3
"""
iPhone Messages Export Tool
Extracts SMS/iMessage data from iOS sms.db SQLite database.

Usage:
    python iphone_messages_export.py /path/to/sms.db --output ./export

The sms.db file is typically located in an unencrypted iPhone backup at:
    Mac: ~/Library/Application Support/MobileSync/Backup/<device-id>/3d/3d0d7e5fb2ce288813306e4d4636395e047a3d28
    Windows: %APPDATA%\Apple Computer\MobileSync\Backup\<device-id>\3d\3d0d7e5fb2ce288813306e4d4636395e047a3d28
"""

import sqlite3
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional


# Apple's Core Data epoch: 2001-01-01 00:00:00 UTC
# Difference from Unix epoch (1970-01-01) in seconds
APPLE_EPOCH_OFFSET = 978307200


def apple_timestamp_to_datetime(timestamp: Optional[int]) -> Optional[str]:
    """Convert Apple Core Data timestamp to ISO 8601 string.

    iOS timestamps can be in seconds or nanoseconds since 2001-01-01.
    Timestamps > 1e12 are in nanoseconds.
    """
    if timestamp is None or timestamp == 0:
        return None

    # Convert nanoseconds to seconds if needed
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
    handle: Optional[str]  # Phone number or email
    service: str  # iMessage or SMS
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


def extract_messages(db_path: str) -> list[Message]:
    """Extract all messages from the sms.db database."""

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Main query joining messages with handles and chats
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

    # Get attachments for each message
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

    # Group attachments by message_id
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

    # Build message objects
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


def extract_contacts(db_path: str) -> list[dict]:
    """Extract all handles (contacts) from the database."""

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
    SELECT
        ROWID as id,
        id as identifier,
        uncanonicalized_id,
        service,
        country
    FROM handle
    ORDER BY ROWID
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def extract_chats(db_path: str) -> list[dict]:
    """Extract all chat/conversation metadata."""

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
    SELECT
        ROWID as id,
        guid,
        chat_identifier,
        display_name,
        service_name,
        group_id,
        is_archived
    FROM chat
    ORDER BY ROWID
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def export_to_json(data: list, output_path: Path) -> None:
    """Export data to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"Exported {len(data)} records to {output_path}")


def format_datetime_for_display(iso_date: Optional[str]) -> str:
    """Format ISO datetime string for human-readable display."""
    if not iso_date:
        return ""
    try:
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return iso_date


def export_to_markdown(messages: list[Message], output_dir: Path) -> None:
    """Export messages to individual markdown files per conversation."""

    if not messages:
        print("No messages to export")
        return

    # Group messages by conversation
    conversations: dict[str, list[Message]] = {}

    for msg in messages:
        key = msg.chat_identifier or msg.handle or 'unknown'
        safe_key = "".join(c if c.isalnum() or c in '-_+' else '_' for c in key)

        if safe_key not in conversations:
            conversations[safe_key] = []
        conversations[safe_key].append(msg)

    md_dir = output_dir / 'markdown'
    md_dir.mkdir(exist_ok=True)

    for conv_id, conv_messages in conversations.items():
        output_path = md_dir / f"{conv_id}.md"

        # Gather metadata
        dates = [m.date for m in conv_messages if m.date]
        services = set(m.service for m in conv_messages if m.service)
        handles = set(m.handle for m in conv_messages if m.handle)
        sent_count = sum(1 for m in conv_messages if m.is_from_me)
        received_count = len(conv_messages) - sent_count
        attachment_count = sum(1 for m in conv_messages if m.attachments)

        # Build markdown content
        lines = []

        # YAML frontmatter
        lines.append("---")
        lines.append(f"conversation: {conv_id}")
        if handles:
            lines.append(f"participants: {', '.join(sorted(handles))}")
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
        display_name = conv_messages[0].chat_display_name
        if display_name:
            lines.append(f"# {display_name}")
        else:
            lines.append(f"# {conv_id}")
        lines.append("")

        # Messages
        for msg in conv_messages:
            timestamp = format_datetime_for_display(msg.date)
            sender = "**Me**" if msg.is_from_me else f"**{msg.handle or 'Unknown'}**"

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

    print(f"Exported {len(conversations)} conversations to {md_dir}")


def export_conversations(messages: list[Message], output_dir: Path) -> None:
    """Export messages grouped by conversation to separate files."""

    conversations: dict[str, list[Message]] = {}

    for msg in messages:
        # Use chat_identifier or handle as conversation key
        key = msg.chat_identifier or msg.handle or 'unknown'
        # Sanitize for filename
        safe_key = "".join(c if c.isalnum() or c in '-_+' else '_' for c in key)

        if safe_key not in conversations:
            conversations[safe_key] = []
        conversations[safe_key].append(msg)

    conv_dir = output_dir / 'conversations'
    conv_dir.mkdir(exist_ok=True)

    for conv_id, conv_messages in conversations.items():
        output_path = conv_dir / f"{conv_id}.json"
        export_to_json([asdict(m) for m in conv_messages], output_path)

    print(f"Exported {len(conversations)} conversations to {conv_dir}")


def print_stats(messages: list[Message], contacts: list[dict], chats: list[dict]) -> None:
    """Print summary statistics."""

    print("\n" + "=" * 50)
    print("EXPORT SUMMARY")
    print("=" * 50)
    print(f"Total messages: {len(messages)}")
    print(f"Total contacts/handles: {len(contacts)}")
    print(f"Total chats/conversations: {len(chats)}")

    if messages:
        sent = sum(1 for m in messages if m.is_from_me)
        received = len(messages) - sent
        print(f"Messages sent: {sent}")
        print(f"Messages received: {received}")

        imessage = sum(1 for m in messages if m.service == 'iMessage')
        sms = sum(1 for m in messages if m.service == 'SMS')
        print(f"iMessages: {imessage}")
        print(f"SMS: {sms}")

        with_attachments = sum(1 for m in messages if m.attachments)
        print(f"Messages with attachments: {with_attachments}")

        dates = [m.date for m in messages if m.date]
        if dates:
            print(f"Date range: {min(dates)} to {max(dates)}")

    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description='Extract iPhone messages from sms.db',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'database',
        help='Path to sms.db file'
    )
    parser.add_argument(
        '--output', '-o',
        default='./messages_export',
        help='Output directory (default: ./messages_export)'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['all', 'json', 'md'],
        default='all',
        help='Export format (default: all)'
    )
    parser.add_argument(
        '--conversations', '-c',
        action='store_true',
        help='Also export messages grouped by conversation'
    )

    args = parser.parse_args()

    db_path = Path(args.database)
    if not db_path.exists():
        print(f"Error: Database file not found: {db_path}")
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Extracting from: {db_path}")
    print(f"Output directory: {output_dir}")

    # Extract data
    messages = extract_messages(str(db_path))
    contacts = extract_contacts(str(db_path))
    chats = extract_chats(str(db_path))

    # Export based on format
    if args.format in ('all', 'json'):
        export_to_json([asdict(m) for m in messages], output_dir / 'messages.json')
        export_to_json(contacts, output_dir / 'contacts.json')
        export_to_json(chats, output_dir / 'chats.json')

    if args.format in ('all', 'md'):
        export_to_markdown(messages, output_dir)

    if args.conversations:
        export_conversations(messages, output_dir)

    print_stats(messages, contacts, chats)

    return 0


if __name__ == '__main__':
    exit(main())
