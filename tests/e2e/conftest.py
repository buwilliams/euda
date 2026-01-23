"""Playwright E2E test fixtures."""

import os
from typing import Generator

import pytest
from playwright.sync_api import Page, BrowserContext, expect

# Default test server URL and password
DEFAULT_BASE_URL = "http://localhost:8000"
TEST_PASSWORD = os.environ.get("EUNO_TEST_PASSWORD", "test")


@pytest.fixture(scope="session")
def browser_context_args():
    """Configure browser context for all tests."""
    return {
        "viewport": {"width": 390, "height": 844},  # Mobile-first viewport
        "ignore_https_errors": True,
    }


@pytest.fixture(scope="session")
def base_url():
    """Get the base URL for tests. Uses EUNO_TEST_URL env var or default."""
    return os.environ.get("EUNO_TEST_URL", DEFAULT_BASE_URL)


@pytest.fixture
def authenticated_page(page: Page, base_url: str) -> Page:
    """Page that is already authenticated (logged in).

    Use this fixture when your test needs to start from a logged-in state.
    """
    page.goto(base_url)

    # Wait for either login overlay or app container
    page.wait_for_selector('[data-testid="login-overlay"], [data-testid="app-container"]')

    # If login overlay is visible, perform login
    if page.locator('[data-testid="login-overlay"]').is_visible():
        page.locator('[data-testid="login-password"]').fill(TEST_PASSWORD)
        page.locator('[data-testid="login-btn"]').click()

        # Wait for app container to be visible (login successful)
        page.wait_for_selector('[data-testid="app-container"]', state="visible", timeout=10000)

    return page


@pytest.fixture
def unauthenticated_page(page: Page, base_url: str) -> Page:
    """Page that starts at the login screen.

    Use this fixture when testing login/authentication flows.
    """
    page.goto(base_url)

    # Wait for page to load
    page.wait_for_selector('[data-testid="login-overlay"], [data-testid="app-container"]')

    return page


def get_by_testid(page: Page, testid: str):
    """Helper to get element by data-testid."""
    return page.locator(f'[data-testid="{testid}"]')


def wait_for_testid(page: Page, testid: str, timeout: float = 5000):
    """Helper to wait for element with data-testid."""
    return get_by_testid(page, testid).wait_for(state="visible", timeout=timeout)
