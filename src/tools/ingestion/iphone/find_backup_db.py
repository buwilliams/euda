#!/usr/bin/env python3
"""
iPhone Backup Locator
Finds the sms.db file and other useful databases in iPhone backups.

Usage:
    python find_backup_db.py                    # Searches default backup locations
    python find_backup_db.py /path/to/backup    # Search specific backup folder
"""

import sqlite3
import sys
import platform
from pathlib import Path
from datetime import datetime


# Known file hashes in iPhone backups
KNOWN_FILES = {
    # Messages
    '3d0d7e5fb2ce288813306e4d4636395e047a3d28': 'sms.db (Messages)',
    # Contacts
    '31bb7ba8914766d4ba40d6dfb6113c8b614be442': 'AddressBook.sqlitedb (Contacts)',
    # Call History
    '2b2b0084a1bc3a5ac8c27afdf14afb42c61a19ca': 'CallHistory.storedata (Call History)',
    # Notes
    'ca3bc056d4da0bbf88b5fb3be254f3b7147e639c': 'NoteStore.sqlite (Notes)',
    # Calendar
    '2041457d5fe04d39d0ab481178355df6781e6858': 'Calendar.sqlitedb (Calendar)',
    # Safari
    'e74113c185fd8297e140cfcf9c99436c5cc06b57': 'History.db (Safari History)',
    # Photos
    '12b144c0bd44f2b3dffd9186d3f9c05b917571a6': 'Photos.sqlite (Photos)',
    # Health
    'healthdb_secure.sqlite': 'Health data',
    # Voicemail
    '992df473bbb9e132f4b3b6e4d33f72171e97bc7a': 'voicemail.db (Voicemail)',
}


def is_wsl() -> bool:
    """Detect if running under Windows Subsystem for Linux."""
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower() or 'wsl' in f.read().lower()
    except FileNotFoundError:
        return False


def get_windows_username_wsl() -> str | None:
    """Get Windows username when running under WSL."""
    import subprocess
    try:
        result = subprocess.run(
            ['cmd.exe', '/c', 'echo %USERNAME%'],
            capture_output=True, text=True, timeout=5
        )
        username = result.stdout.strip()
        if username and username != '%USERNAME%':
            return username
    except Exception:
        pass

    # Fallback: try to find user directories in /mnt/c/Users
    users_dir = Path('/mnt/c/Users')
    if users_dir.exists():
        for user_dir in users_dir.iterdir():
            if user_dir.is_dir() and user_dir.name not in ('Public', 'Default', 'Default User', 'All Users'):
                # Check if this looks like a real user directory
                if (user_dir / 'AppData').exists():
                    return user_dir.name
    return None


def get_default_backup_paths() -> list[Path]:
    """Get default backup directory paths based on OS."""

    paths = []
    system = platform.system()

    if system == 'Darwin':  # macOS
        home = Path.home()
        paths.append(home / 'Library' / 'Application Support' / 'MobileSync' / 'Backup')
    elif system == 'Windows':
        # Try multiple Windows paths
        appdata = Path.home() / 'AppData' / 'Roaming'
        paths.append(appdata / 'Apple Computer' / 'MobileSync' / 'Backup')
        paths.append(appdata / 'Apple' / 'MobileSync' / 'Backup')
    elif system == 'Linux':
        # Check for WSL first
        if is_wsl():
            username = get_windows_username_wsl()
            if username:
                # WSL mounts Windows drives under /mnt/
                wsl_userprofile = Path(f'/mnt/c/Users/{username}')
                wsl_appdata = wsl_userprofile / 'AppData' / 'Roaming'

                # Microsoft Store iTunes version (%userprofile%\Apple\MobileSync\Backup)
                paths.append(wsl_userprofile / 'Apple' / 'MobileSync' / 'Backup')

                # Standard iTunes install (%appdata%\Apple Computer\MobileSync\Backup)
                paths.append(wsl_appdata / 'Apple Computer' / 'MobileSync' / 'Backup')
                paths.append(wsl_appdata / 'Apple' / 'MobileSync' / 'Backup')
            else:
                # Try common usernames or let user know
                print("WSL detected but couldn't determine Windows username.")
                print("You can specify the backup path directly as an argument.")

        # Wine or other emulation
        home = Path.home()
        paths.append(home / '.wine' / 'drive_c' / 'users' / 'Public' / 'Apple' / 'MobileSync' / 'Backup')

    return paths


def find_manifest_db(backup_dir: Path) -> Path | None:
    """Find the Manifest.db file in a backup."""
    manifest = backup_dir / 'Manifest.db'
    if manifest.exists():
        return manifest
    return None


def get_backup_info(backup_dir: Path) -> dict | None:
    """Get information about an iPhone backup."""

    info_plist = backup_dir / 'Info.plist'
    manifest_db = find_manifest_db(backup_dir)

    info = {
        'path': backup_dir,
        'has_manifest': manifest_db is not None,
        'encrypted': False,
        'files_found': []
    }

    # Check if backup is encrypted
    manifest_plist = backup_dir / 'Manifest.plist'
    if manifest_plist.exists():
        try:
            import plistlib
            with open(manifest_plist, 'rb') as f:
                manifest = plistlib.load(f)
                info['encrypted'] = manifest.get('IsEncrypted', False)
        except Exception:
            pass

    # Try to get device info
    if info_plist.exists():
        try:
            import plistlib
            with open(info_plist, 'rb') as f:
                plist = plistlib.load(f)
                info['device_name'] = plist.get('Device Name', 'Unknown')
                info['product_type'] = plist.get('Product Type', 'Unknown')
                info['ios_version'] = plist.get('Product Version', 'Unknown')
                info['last_backup'] = plist.get('Last Backup Date', None)
        except Exception:
            pass

    return info


def search_for_known_files(backup_dir: Path) -> list[tuple[str, Path]]:
    """Search for known database files in backup."""

    found = []

    for file_hash, description in KNOWN_FILES.items():
        # Check in subdirectory structure (newer backups)
        subdir = backup_dir / file_hash[:2] / file_hash
        if subdir.exists():
            found.append((description, subdir))
            continue

        # Check flat structure (older backups)
        flat = backup_dir / file_hash
        if flat.exists():
            found.append((description, flat))
            continue

    return found


def search_manifest_db(manifest_path: Path, search_term: str = 'sms') -> list[tuple[str, str]]:
    """Search the Manifest.db for files matching search term."""

    results = []

    try:
        conn = sqlite3.connect(str(manifest_path))
        cursor = conn.cursor()

        query = """
        SELECT fileID, relativePath, flags, domain
        FROM Files
        WHERE relativePath LIKE ?
        ORDER BY relativePath
        """

        cursor.execute(query, (f'%{search_term}%',))

        for row in cursor.fetchall():
            file_id, rel_path, flags, domain = row
            results.append((file_id, f"{domain}: {rel_path}"))

        conn.close()
    except Exception as e:
        print(f"Error reading Manifest.db: {e}")

    return results


def main():
    search_paths = []

    if len(sys.argv) > 1:
        # Use provided path
        search_paths = [Path(sys.argv[1])]
    else:
        # Use default paths
        search_paths = get_default_backup_paths()

    print("iPhone Backup Database Locator")
    print("=" * 60)

    all_backups = []

    for base_path in search_paths:
        if not base_path.exists():
            continue

        print(f"\nSearching: {base_path}")

        # Each subdirectory is a different device backup
        for item in base_path.iterdir():
            if item.is_dir():
                # Check if it looks like a backup (has Manifest.db or Manifest.plist)
                has_manifest = (item / 'Manifest.db').exists() or (item / 'Manifest.plist').exists()
                # Also accept by name pattern: 40-char UDID or newer formats like 00008101-XXXXX
                looks_like_backup = len(item.name) == 40 or item.name.startswith('0000')
                if has_manifest or looks_like_backup:
                    all_backups.append(item)

    if not all_backups:
        print("\nNo iPhone backups found!")
        print("\nDefault search locations:")
        for p in get_default_backup_paths():
            print(f"  {p}")
        print("\nMake sure you have created an unencrypted backup via iTunes/Finder.")
        return 1

    print(f"\nFound {len(all_backups)} backup(s):\n")

    sms_db_found = None

    for backup_dir in all_backups:
        info = get_backup_info(backup_dir)

        print("-" * 60)
        print(f"Backup: {backup_dir.name}")
        if 'device_name' in info:
            print(f"  Device: {info.get('device_name')} ({info.get('product_type')})")
            print(f"  iOS: {info.get('ios_version')}")
        if info.get('last_backup'):
            print(f"  Last backup: {info['last_backup']}")

        if info.get('encrypted'):
            print("  WARNING: ENCRYPTED - Cannot extract databases!")
            print("      Disable encryption in iTunes/Finder and backup again.")
            continue

        print("\n  Found databases:")
        found_files = search_for_known_files(backup_dir)

        if found_files:
            for desc, path in found_files:
                print(f"    [OK] {desc}")
                print(f"      {path}")
                if 'sms.db' in desc:
                    sms_db_found = path
        else:
            print("    None of the known databases found")

            # Try searching manifest
            manifest = find_manifest_db(backup_dir)
            if manifest:
                print("\n  Searching Manifest.db for message databases...")
                results = search_manifest_db(manifest, 'sms')
                for file_id, path in results[:5]:
                    full_path = backup_dir / file_id[:2] / file_id
                    exists = "[OK]" if full_path.exists() else "[MISSING]"
                    print(f"    {exists} {path}")
                    print(f"      {full_path}")

    print("\n" + "=" * 60)

    if sms_db_found:
        print("\n[OK] To extract messages, run:")
        print(f'  python iphone_messages_export.py "{sms_db_found}" --output ./export --conversations')
    else:
        print("\n[FAIL] sms.db not found. Possible reasons:")
        print("  - Backup is encrypted (create new unencrypted backup)")
        print("  - Backup is incomplete")
        print("  - Different iOS version with different file structure")

    return 0


if __name__ == '__main__':
    exit(main())
