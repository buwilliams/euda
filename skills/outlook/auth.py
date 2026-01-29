"""OAuth2 authentication using MSAL for Microsoft Graph API."""

import os
from typing import Optional

import msal

from skills.outlook.storage import load_token_cache, save_token_cache

# OAuth2 scopes for Microsoft Graph
SCOPES = [
    "User.Read",
    "Mail.Read",
    "Mail.Send",
    "Calendars.ReadWrite",
    "Contacts.Read",
    "offline_access",  # Required for refresh tokens
]


def get_client_id() -> Optional[str]:
    """Get Microsoft client ID from environment."""
    return os.environ.get("MICROSOFT_CLIENT_ID")


def get_msal_app(account_name: str) -> Optional[msal.PublicClientApplication]:
    """Get MSAL application with token cache for an account.

    Args:
        account_name: Name of the account

    Returns:
        MSAL PublicClientApplication, or None if client ID not configured
    """
    client_id = get_client_id()
    if not client_id:
        return None

    # Create token cache
    cache = msal.SerializableTokenCache()

    # Load existing cache if available
    cache_data = load_token_cache(account_name)
    if cache_data:
        cache.deserialize(cache_data)

    # Create MSAL app with cache
    app = msal.PublicClientApplication(
        client_id,
        authority="https://login.microsoftonline.com/common",
        token_cache=cache,
    )

    return app


def run_oauth_flow(account_name: str) -> dict:
    """Run interactive OAuth flow using device code.

    This flow is user-friendly for CLI apps - it displays a code
    that the user enters at microsoft.com/devicelogin.

    Args:
        account_name: Name for this account

    Returns:
        Dict with 'access_token' on success, or 'error' on failure
    """
    client_id = get_client_id()
    if not client_id:
        return {"error": "MICROSOFT_CLIENT_ID environment variable not set"}

    app = get_msal_app(account_name)
    if not app:
        return {"error": "Failed to create MSAL application"}

    # Initiate device code flow
    flow = app.initiate_device_flow(scopes=SCOPES)

    if "user_code" not in flow:
        return {"error": f"Failed to initiate device flow: {flow.get('error_description', 'Unknown error')}"}

    # Display instructions to user
    print()
    print("To authenticate, open a browser and go to:")
    print(f"  {flow['verification_uri']}")
    print()
    print(f"Enter this code: {flow['user_code']}")
    print()
    print("Waiting for authentication...")

    # Wait for user to complete authentication
    result = app.acquire_token_by_device_flow(flow)

    if "access_token" in result:
        # Save the token cache
        save_token_cache(account_name, app.token_cache.serialize())
        return result
    else:
        error_msg = result.get("error_description", result.get("error", "Unknown error"))
        return {"error": error_msg}


def get_access_token(account_name: str) -> Optional[str]:
    """Get valid access token for an account, refreshing if needed.

    Args:
        account_name: Name of the account

    Returns:
        Access token string, or None if not authenticated
    """
    app = get_msal_app(account_name)
    if not app:
        return None

    # Get accounts from cache
    accounts = app.get_accounts()
    if not accounts:
        return None

    # Try to get token silently (from cache or via refresh)
    result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if result and "access_token" in result:
        # Save updated cache (in case token was refreshed)
        save_token_cache(account_name, app.token_cache.serialize())
        return result["access_token"]

    return None


def validate_credentials(account_name: str) -> bool:
    """Check if an account has valid credentials.

    Args:
        account_name: Name of the account

    Returns:
        True if credentials are valid or can be refreshed
    """
    token = get_access_token(account_name)
    return token is not None
