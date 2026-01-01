"""
iPhone Backup Extraction Tools

Standalone scripts for extracting data from iOS device backups.
These tools read SQLite databases from unencrypted iPhone backups
and export messages, contacts, media, and metadata.

Scripts:
    iphone_backup.py        - Main entry point, extracts messages and media
    find_backup_db.py       - Utility to locate iPhone backups and databases
    iphone_messages_export.py - Direct sms.db export (without contact lookup)

Usage:
    # Auto-find backup and export everything
    python -m src.tools.archivist.iphone.iphone_backup

    # Find available backups
    python -m src.tools.archivist.iphone.find_backup_db

    # Export from specific sms.db
    python -m src.tools.archivist.iphone.iphone_messages_export /path/to/sms.db

Key Technical Details:
    - iOS backup files are stored with SHA-1 hash names
    - Apple timestamps are seconds/nanoseconds since 2001-01-01
    - sms.db hash: 3d0d7e5fb2ce288813306e4d4636395e047a3d28
    - AddressBook.sqlitedb hash: 31bb7ba8914766d4ba40d6dfb6113c8b614be442
    - Encrypted backups cannot be read - requires unencrypted backup
"""
