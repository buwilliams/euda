#!/usr/bin/env python3
"""Export mbox emails to individual .txt files, filtering spam/trash."""

import mailbox
import os
import re
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime
from pathlib import Path


def decode_mime_header(header):
    """Decode a MIME-encoded header to string."""
    if header is None:
        return ""
    decoded_parts = []
    for part, charset in decode_header(header):
        if isinstance(part, bytes):
            try:
                decoded_parts.append(part.decode(charset or 'utf-8', errors='replace'))
            except (LookupError, TypeError):
                decoded_parts.append(part.decode('utf-8', errors='replace'))
        else:
            decoded_parts.append(part)
    return ' '.join(decoded_parts)


def get_text_content(msg):
    """Extract text content from email message."""
    text_parts = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # Skip attachments
            if "attachment" in content_disposition:
                continue

            # Get text/plain parts
            if content_type == "text/plain":
                try:
                    charset = part.get_content_charset() or 'utf-8'
                    payload = part.get_payload(decode=True)
                    if payload:
                        text_parts.append(payload.decode(charset, errors='replace'))
                except Exception:
                    pass
            # Fallback to text/html if no plain text
            elif content_type == "text/html" and not text_parts:
                try:
                    charset = part.get_content_charset() or 'utf-8'
                    payload = part.get_payload(decode=True)
                    if payload:
                        html = payload.decode(charset, errors='replace')
                        # Basic HTML stripping
                        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
                        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
                        text = re.sub(r'<[^>]+>', ' ', text)
                        text = re.sub(r'&nbsp;', ' ', text)
                        text = re.sub(r'&amp;', '&', text)
                        text = re.sub(r'&lt;', '<', text)
                        text = re.sub(r'&gt;', '>', text)
                        text = re.sub(r'\s+', ' ', text).strip()
                        text_parts.append(text)
                except Exception:
                    pass
    else:
        # Not multipart
        content_type = msg.get_content_type()
        try:
            charset = msg.get_content_charset() or 'utf-8'
            payload = msg.get_payload(decode=True)
            if payload:
                if content_type == "text/plain":
                    text_parts.append(payload.decode(charset, errors='replace'))
                elif content_type == "text/html":
                    html = payload.decode(charset, errors='replace')
                    text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
                    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = re.sub(r'&nbsp;', ' ', text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    text_parts.append(text)
        except Exception:
            pass

    return '\n\n'.join(text_parts)


def is_spam_or_trash(msg):
    """Check if email is in Spam or Trash folder based on Gmail labels."""
    labels = msg.get('X-Gmail-Labels', '')
    if not labels:
        return False

    labels_lower = labels.lower()
    spam_trash_indicators = ['spam', 'trash', 'junk', 'deleted']

    for indicator in spam_trash_indicators:
        if indicator in labels_lower:
            return True

    return False


def sanitize_filename(name, max_length=50):
    """Create a safe filename from string."""
    # Remove or replace invalid characters
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)
    name = name.strip('. ')
    if len(name) > max_length:
        name = name[:max_length]
    return name or "no_subject"


def format_email_txt(msg, msg_id):
    """Format email as plain text."""
    from_addr = decode_mime_header(msg.get('From', ''))
    to_addr = decode_mime_header(msg.get('To', ''))
    cc_addr = decode_mime_header(msg.get('Cc', ''))
    subject = decode_mime_header(msg.get('Subject', '(No Subject)'))
    date_str = msg.get('Date', '')

    # Parse date
    try:
        date_obj = parsedate_to_datetime(date_str)
        formatted_date = date_obj.strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception:
        formatted_date = date_str

    # Get body
    body = get_text_content(msg)

    # Build output
    lines = [
        f"Subject: {subject}",
        f"From: {from_addr}",
        f"To: {to_addr}",
    ]

    if cc_addr:
        lines.append(f"Cc: {cc_addr}")

    lines.extend([
        f"Date: {formatted_date}",
        "",
        "-" * 60,
        "",
        body if body else "(No text content)",
    ])

    return '\n'.join(lines)


def main():
    mbox_path = "/mnt/d/Lifelog/text_content/clean/email/gmail/Google_All mail Including Spam and Trash-002.mbox"
    output_dir = Path("/mnt/d/Lifelog/text_content/clean/email/gmail/emails")

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    print(f"Opening mbox file: {mbox_path}")
    print("Counting emails...")

    # First pass: count total and non-spam emails
    mbox = mailbox.mbox(mbox_path)
    total_count = len(mbox)
    print(f"Total emails in mbox: {total_count}")

    # Second pass: export
    exported = 0
    skipped_spam = 0
    skipped_empty = 0
    errors = 0

    print("Exporting emails (excluding spam/trash)...")

    for i, msg in enumerate(mbox, 1):
        try:
            # Skip spam/trash
            if is_spam_or_trash(msg):
                skipped_spam += 1
                if i % 1000 == 0:
                    print(f"Processing {i} of {total_count}... (exported: {exported}, spam/trash: {skipped_spam})")
                continue

            # Get date for filename
            date_str = msg.get('Date', '')
            try:
                date_obj = parsedate_to_datetime(date_str)
                date_prefix = date_obj.strftime('%Y%m%d_%H%M%S')
            except Exception:
                date_prefix = f"unknown_{i:06d}"

            # Get subject for filename
            subject = decode_mime_header(msg.get('Subject', 'no_subject'))
            safe_subject = sanitize_filename(subject, max_length=40)

            # Create unique filename
            filename = f"{date_prefix}_{safe_subject}.txt"
            filepath = output_dir / filename

            # Handle duplicates
            counter = 1
            while filepath.exists():
                filename = f"{date_prefix}_{safe_subject}_{counter}.txt"
                filepath = output_dir / filename
                counter += 1

            # Format and write
            content = format_email_txt(msg, i)

            # Skip if essentially empty
            if len(content.strip()) < 100:
                skipped_empty += 1
                continue

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            exported += 1

            if exported % 100 == 0:
                print(f"{exported} of ~{total_count - skipped_spam} created (processing {i}/{total_count})")

        except Exception as e:
            errors += 1
            if errors <= 10:
                print(f"Error processing email {i}: {e}")

    print()
    print("=" * 60)
    print(f"Export complete!")
    print(f"  Total in mbox:     {total_count}")
    print(f"  Exported:          {exported}")
    print(f"  Skipped (spam):    {skipped_spam}")
    print(f"  Skipped (empty):   {skipped_empty}")
    print(f"  Errors:            {errors}")
    print(f"  Output directory:  {output_dir}")


if __name__ == "__main__":
    main()
