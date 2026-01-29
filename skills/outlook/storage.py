"""Storage for Outlook skill - config and token persistence."""

import json
import os
from pathlib import Path
from typing import Optional


def _get_skill_dir() -> Path:
    """Get the skill data directory."""
    data_dir = os.environ.get("EUNO_DATA_DIR")
    if data_dir:
        base = Path(data_dir)
    else:
        base = Path(__file__).parent.parent.parent / "data"

    skill_dir = base / "skills" / "outlook"
    skill_dir.mkdir(parents=True, exist_ok=True)
    return skill_dir


def _get_accounts_dir() -> Path:
    """Get the accounts directory."""
    accounts_dir = _get_skill_dir() / "accounts"
    accounts_dir.mkdir(parents=True, exist_ok=True)
    return accounts_dir


def _get_config_path() -> Path:
    """Get the config file path."""
    return _get_skill_dir() / "config.json"


def load_config() -> dict:
    """Load skill configuration."""
    config_path = _get_config_path()
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {"default_account": None}


def save_config(config: dict) -> None:
    """Save skill configuration."""
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
            # Check for token cache file
            if (d / "token_cache.json").exists():
                accounts.append(d.name)
    return accounts


def account_exists(account_name: str) -> bool:
    """Check if an account exists."""
    account_dir = _get_accounts_dir() / account_name
    return (account_dir / "token_cache.json").exists()


def get_token_cache_path(account_name: str) -> Path:
    """Get the token cache file path for an account."""
    account_dir = _get_accounts_dir() / account_name
    account_dir.mkdir(parents=True, exist_ok=True)
    return account_dir / "token_cache.json"


def load_token_cache(account_name: str) -> Optional[str]:
    """Load MSAL token cache for an account.

    Returns:
        Serialized token cache string, or None if not found
    """
    token_path = get_token_cache_path(account_name)
    if token_path.exists():
        return token_path.read_text()
    return None


def save_token_cache(account_name: str, cache_data: str) -> None:
    """Save MSAL token cache for an account.

    Args:
        account_name: Name of the account
        cache_data: Serialized token cache string from MSAL
    """
    token_path = get_token_cache_path(account_name)
    token_path.write_text(cache_data)


def delete_account(account_name: str) -> bool:
    """Delete an account and its tokens."""
    account_dir = _get_accounts_dir() / account_name
    if not account_dir.exists():
        return False

    # Remove token cache file
    token_path = account_dir / "token_cache.json"
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


def get_account_info(account_name: str) -> Optional[dict]:
    """Get info about an account.

    Returns dict with:
        - email: account email (if available from token cache)
    """
    if not account_exists(account_name):
        return None

    info = {"name": account_name}

    # Try to get email from token cache metadata
    cache_data = load_token_cache(account_name)
    if cache_data:
        try:
            cache = json.loads(cache_data)
            # MSAL stores account info in the cache
            accounts = cache.get("Account", {})
            if accounts:
                # Get first account's info
                for key, account in accounts.items():
                    if "username" in account:
                        info["email"] = account["username"]
                        break
        except (json.JSONDecodeError, KeyError):
            pass

    return info
