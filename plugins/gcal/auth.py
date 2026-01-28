"""OAuth2 authentication flow for Google Calendar."""

import os
from datetime import datetime, timezone
from typing import Optional, Union

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow

from plugins.gcal.storage import (
    load_token,
    save_token,
    get_account_type,
    get_service_account_path,
    ACCOUNT_TYPE_SERVICE,
    ACCOUNT_TYPE_OAUTH,
)

# OAuth2 scopes for Google Calendar
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


def get_client_config() -> Optional[dict]:
    """Get OAuth client configuration from environment variables."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def credentials_to_dict(creds: Credentials) -> dict:
    """Convert Credentials object to dictionary for storage."""
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }


def credentials_from_dict(token_data: dict) -> Credentials:
    """Create Credentials object from stored dictionary."""
    expiry = None
    if token_data.get("expiry"):
        expiry = datetime.fromisoformat(token_data["expiry"])
        # Ensure timezone awareness
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

    return Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", SCOPES),
        expiry=expiry,
    )


def run_oauth_flow(account_name: str) -> Optional[Credentials]:
    """Run the OAuth2 flow for a new account.

    Args:
        account_name: Name for this account

    Returns:
        Credentials if successful, None if failed
    """
    client_config = get_client_config()
    if not client_config:
        print("Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set.")
        print("Create OAuth credentials at https://console.cloud.google.com/apis/credentials")
        return None

    try:
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        # Run local server for OAuth callback
        creds = flow.run_local_server(port=0)

        # Save the credentials
        save_token(account_name, credentials_to_dict(creds))

        return creds
    except Exception as e:
        print(f"OAuth flow failed: {e}")
        return None


def get_credentials(account_name: str, auto_refresh: bool = True) -> Optional[Union[Credentials, service_account.Credentials]]:
    """Get credentials for an account, refreshing if needed.

    Args:
        account_name: Name of the account
        auto_refresh: Whether to automatically refresh expired tokens

    Returns:
        Credentials if valid, None if not found or refresh failed
    """
    account_type = get_account_type(account_name)

    if account_type == ACCOUNT_TYPE_SERVICE:
        return get_service_account_credentials(account_name)

    if account_type == ACCOUNT_TYPE_OAUTH:
        return get_oauth_credentials(account_name, auto_refresh)

    return None


def get_oauth_credentials(account_name: str, auto_refresh: bool = True) -> Optional[Credentials]:
    """Get OAuth credentials for an account, refreshing if needed."""
    token_data = load_token(account_name)
    if not token_data:
        return None

    creds = credentials_from_dict(token_data)

    # Check if credentials need refresh
    if creds.expired and creds.refresh_token and auto_refresh:
        try:
            creds.refresh(Request())
            # Save the refreshed credentials
            save_token(account_name, credentials_to_dict(creds))
        except Exception as e:
            print(f"Token refresh failed for account '{account_name}': {e}")
            return None

    return creds


def get_service_account_credentials(account_name: str) -> Optional[service_account.Credentials]:
    """Get service account credentials for an account.

    Args:
        account_name: Name of the account

    Returns:
        Service account credentials if valid, None if not found
    """
    sa_path = get_service_account_path(account_name)
    if not sa_path.exists():
        return None

    try:
        creds = service_account.Credentials.from_service_account_file(
            str(sa_path),
            scopes=SCOPES,
        )
        return creds
    except Exception as e:
        print(f"Failed to load service account credentials for '{account_name}': {e}")
        return None


def validate_credentials(account_name: str) -> bool:
    """Check if an account has valid credentials.

    Args:
        account_name: Name of the account

    Returns:
        True if credentials are valid or can be refreshed
    """
    creds = get_credentials(account_name)
    if creds is None:
        return False

    # Service account credentials are always valid if loaded
    if isinstance(creds, service_account.Credentials):
        return True

    return creds.valid
