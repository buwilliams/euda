"""Storage for Google Calendar plugin - config and token persistence."""

import json
import os
import shutil
from pathlib import Path
from typing import Optional


# Account types
ACCOUNT_TYPE_OAUTH = "oauth"
ACCOUNT_TYPE_SERVICE = "service_account"


def _get_plugin_dir() -> Path:
    """Get the plugin data directory."""
    data_dir = os.environ.get("EUNO_DATA_DIR")
    if data_dir:
        base = Path(data_dir)
    else:
        base = Path(__file__).parent.parent.parent / "data"

    plugin_dir = base / "plugins" / "gcal"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    return plugin_dir


def _get_accounts_dir() -> Path:
    """Get the accounts directory."""
    accounts_dir = _get_plugin_dir() / "accounts"
    accounts_dir.mkdir(parents=True, exist_ok=True)
    return accounts_dir


def _get_config_path() -> Path:
    """Get the config file path."""
    return _get_plugin_dir() / "config.json"


def load_config() -> dict:
    """Load plugin configuration."""
    config_path = _get_config_path()
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {"default_account": None}


def save_config(config: dict) -> None:
    """Save plugin configuration."""
    config_path = _get_config_path()
    config_path.write_text(json.dumps(config, indent=2))


def get_default_account() -> Optional[str]:
    """Get the default account name."""
    config = load_config()
    return config.get("default_account")


def set_default_account(account_name: str) -> None:
    """Set the default account name."""
    config = load_config()
    config["default_account"] = account_name
    save_config(config)


def list_accounts() -> list[str]:
    """List all configured account names."""
    accounts_dir = _get_accounts_dir()
    accounts = []
    for d in accounts_dir.iterdir():
        if d.is_dir():
            # Check for OAuth token or service account key
            if (d / "token.json").exists() or (d / "service_account.json").exists():
                accounts.append(d.name)
    return accounts


def account_exists(account_name: str) -> bool:
    """Check if an account exists."""
    account_dir = _get_accounts_dir() / account_name
    return (account_dir / "token.json").exists() or (account_dir / "service_account.json").exists()


def get_account_type(account_name: str) -> Optional[str]:
    """Get the type of an account (oauth or service_account)."""
    account_dir = _get_accounts_dir() / account_name
    if (account_dir / "service_account.json").exists():
        return ACCOUNT_TYPE_SERVICE
    if (account_dir / "token.json").exists():
        return ACCOUNT_TYPE_OAUTH
    return None


def get_token_path(account_name: str) -> Path:
    """Get the token file path for an account."""
    account_dir = _get_accounts_dir() / account_name
    account_dir.mkdir(parents=True, exist_ok=True)
    return account_dir / "token.json"


def load_token(account_name: str) -> Optional[dict]:
    """Load OAuth token for an account."""
    token_path = get_token_path(account_name)
    if token_path.exists():
        return json.loads(token_path.read_text())
    return None


def save_token(account_name: str, token: dict) -> None:
    """Save OAuth token for an account."""
    token_path = get_token_path(account_name)
    token_path.write_text(json.dumps(token, indent=2))


def delete_account(account_name: str) -> bool:
    """Delete an account and its tokens."""
    account_dir = _get_accounts_dir() / account_name
    if not account_dir.exists():
        return False

    # Remove token file
    token_path = account_dir / "token.json"
    if token_path.exists():
        token_path.unlink()

    # Remove account directory
    try:
        account_dir.rmdir()
    except OSError:
        # Directory not empty, remove remaining files
        for f in account_dir.iterdir():
            f.unlink()
        account_dir.rmdir()

    # If this was the default account, clear default
    config = load_config()
    if config.get("default_account") == account_name:
        config["default_account"] = None
        save_config(config)

    return True


def resolve_account(account_name: Optional[str]) -> Optional[str]:
    """Resolve account name: use provided, default, or only available account."""
    if account_name:
        return account_name

    default = get_default_account()
    if default and account_exists(default):
        return default

    # If only one account exists, use it
    accounts = list_accounts()
    if len(accounts) == 1:
        return accounts[0]

    return None


# Service account functions

def get_service_account_path(account_name: str) -> Path:
    """Get the service account key file path for an account."""
    account_dir = _get_accounts_dir() / account_name
    account_dir.mkdir(parents=True, exist_ok=True)
    return account_dir / "service_account.json"


def save_service_account(account_name: str, key_file_path: str) -> bool:
    """Copy service account key file to account storage.

    Args:
        account_name: Name for this account
        key_file_path: Path to the service account JSON key file

    Returns:
        True if successful, False otherwise
    """
    from src.skills.context import resolve_user_path

    source = resolve_user_path(key_file_path)
    if not source.exists():
        return False

    # Validate it's a valid service account file
    try:
        data = json.loads(source.read_text())
        if data.get("type") != "service_account":
            return False
    except (json.JSONDecodeError, KeyError):
        return False

    dest = get_service_account_path(account_name)
    shutil.copy2(source, dest)
    return True


def load_service_account(account_name: str) -> Optional[dict]:
    """Load service account key data for an account."""
    sa_path = get_service_account_path(account_name)
    if sa_path.exists():
        return json.loads(sa_path.read_text())
    return None


def get_account_info(account_name: str) -> Optional[dict]:
    """Get info about an account.

    Returns dict with:
        - type: 'oauth' or 'service_account'
        - email: account email (for service accounts)
    """
    account_type = get_account_type(account_name)
    if not account_type:
        return None

    info = {"type": account_type}

    if account_type == ACCOUNT_TYPE_SERVICE:
        sa_data = load_service_account(account_name)
        if sa_data:
            info["email"] = sa_data.get("client_email", "")
            info["project_id"] = sa_data.get("project_id", "")

    return info


# Calendar configuration functions

def list_configured_calendars() -> dict[str, str]:
    """List all configured calendars.

    Returns:
        Dict mapping calendar name to calendar ID
    """
    config = load_config()
    return config.get("calendars", {})


def add_calendar(name: str, calendar_id: str) -> None:
    """Add a calendar to the configuration.

    Args:
        name: Friendly name for the calendar (e.g., 'primary', 'work')
        calendar_id: Google Calendar ID (usually an email address)
    """
    config = load_config()
    if "calendars" not in config:
        config["calendars"] = {}
    config["calendars"][name] = calendar_id
    save_config(config)


def remove_calendar(name: str) -> bool:
    """Remove a calendar from the configuration.

    Args:
        name: Friendly name of the calendar to remove

    Returns:
        True if removed, False if not found
    """
    config = load_config()
    calendars = config.get("calendars", {})
    if name not in calendars:
        return False
    del calendars[name]
    config["calendars"] = calendars
    save_config(config)
    return True


def get_calendar_id(name: str) -> Optional[str]:
    """Get the calendar ID for a configured calendar name.

    Args:
        name: Friendly name of the calendar

    Returns:
        Calendar ID if found, None otherwise
    """
    calendars = list_configured_calendars()
    return calendars.get(name)


def resolve_calendar(calendar: str) -> str:
    """Resolve a calendar name or ID.

    If the input matches a configured calendar name, returns the calendar ID.
    Otherwise, returns the input as-is (assuming it's already a calendar ID).

    Args:
        calendar: Calendar name or ID

    Returns:
        Calendar ID
    """
    configured_id = get_calendar_id(calendar)
    if configured_id:
        return configured_id
    return calendar
