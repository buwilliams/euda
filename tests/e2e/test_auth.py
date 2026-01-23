"""E2E tests for authentication flows."""

import pytest
import requests
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def is_password_required(base_url: str) -> bool:
    """Check if the server requires password authentication."""
    try:
        response = requests.get(f"{base_url}/api/auth/check", timeout=5)
        data = response.json()
        return data.get("password_required", False)
    except Exception:
        return False


@pytest.fixture
def requires_auth(base_url):
    """Skip test if authentication is not required."""
    if not is_password_required(base_url):
        pytest.skip("Authentication is not required (no password set)")


class TestLoginOverlay:
    """Tests for login overlay appearance and behavior."""

    def test_login_overlay_appears(self, unauthenticated_page: Page, base_url: str, requires_auth):
        """Login overlay should appear when not authenticated."""
        expect(unauthenticated_page.locator('[data-testid="login-overlay"]:not(.hidden)')).to_be_visible()

    def test_login_form_elements_visible(self, unauthenticated_page: Page, base_url: str, requires_auth):
        """Login form should have password input and sign in button."""
        page = unauthenticated_page
        expect(page.locator('[data-testid="login-password"]')).to_be_visible()
        expect(page.locator('[data-testid="login-btn"]')).to_be_visible()


class TestLoginSuccess:
    """Tests for successful login."""

    def test_login_success_shows_app(self, unauthenticated_page: Page, base_url: str, requires_auth):
        """Successful login should show the app container."""
        page = unauthenticated_page

        # Fill in password and submit
        page.locator('[data-testid="login-password"]').fill("test")
        page.locator('[data-testid="login-btn"]').click()

        # App container should be visible after successful login
        expect(page.locator('[data-testid="app-container"]')).to_be_visible(timeout=10000)


class TestLoginFailure:
    """Tests for login failure handling."""

    def test_login_failure_shows_error(self, unauthenticated_page: Page, base_url: str, requires_auth):
        """Failed login should show error message."""
        page = unauthenticated_page

        # Fill in wrong password and submit
        page.locator('[data-testid="login-password"]').fill("wrong-password")
        page.locator('[data-testid="login-btn"]').click()

        # Error message should appear
        # Note: The error element may not have content until login fails
        expect(page.locator('[data-testid="login-error"]')).not_to_be_empty(timeout=5000)


class TestSignOut:
    """Tests for sign out functionality."""

    def test_signout_returns_to_login(self, authenticated_page: Page, base_url: str, requires_auth):
        """Signing out should return to login overlay."""
        page = authenticated_page

        # Open overflow menu and navigate to settings
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-settings"]').click()

        # Wait for settings content
        expect(page.locator('[data-testid="settings-content"]')).to_be_visible(timeout=5000)

        # Click sign out button
        page.locator('[data-testid="signout-btn"]').click()

        # Should return to login overlay (with visible class, not hidden)
        expect(page.locator('[data-testid="login-overlay"]:not(.hidden)')).to_be_visible(timeout=5000)
