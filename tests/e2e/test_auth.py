"""E2E tests for authentication flows."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


class TestLoginOverlay:
    """Tests for login overlay appearance and behavior."""

    def test_login_overlay_appears(self, unauthenticated_page: Page):
        """Login overlay should appear when not authenticated."""
        expect(unauthenticated_page.locator('[data-testid="login-overlay"]')).to_be_visible()

    def test_login_form_elements_visible(self, unauthenticated_page: Page):
        """Login form should have password input and sign in button."""
        page = unauthenticated_page
        expect(page.locator('[data-testid="login-password"]')).to_be_visible()
        expect(page.locator('[data-testid="login-btn"]')).to_be_visible()


class TestLoginSuccess:
    """Tests for successful login."""

    def test_login_success_shows_app(self, unauthenticated_page: Page):
        """Successful login should show the app container."""
        page = unauthenticated_page

        # Fill in password and submit
        page.locator('[data-testid="login-password"]').fill("test")
        page.locator('[data-testid="login-btn"]').click()

        # App container should be visible after successful login
        expect(page.locator('[data-testid="app-container"]')).to_be_visible(timeout=10000)


class TestLoginFailure:
    """Tests for login failure handling."""

    def test_login_failure_shows_error(self, unauthenticated_page: Page):
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

    def test_signout_returns_to_login(self, authenticated_page: Page):
        """Signing out should return to login overlay."""
        page = authenticated_page

        # Open overflow menu and navigate to settings
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-settings"]').click()

        # Wait for settings content
        expect(page.locator('[data-testid="settings-content"]')).to_be_visible(timeout=5000)

        # Click sign out button
        page.locator('[data-testid="signout-btn"]').click()

        # Should return to login overlay
        expect(page.locator('[data-testid="login-overlay"]')).to_be_visible(timeout=5000)
