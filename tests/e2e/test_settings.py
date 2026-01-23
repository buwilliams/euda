"""E2E tests for Settings tab functionality."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


class TestSettingsLoads:
    """Tests for Settings tab loading."""

    def test_settings_loads(self, authenticated_page: Page):
        """Settings tab should load when navigated to."""
        page = authenticated_page

        # Open overflow menu and navigate to settings
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-settings"]').click()

        expect(page.locator('[data-testid="tab-settings"]')).to_be_visible()
        expect(page.locator('[data-testid="settings-content"]')).to_be_visible()


class TestCostsDisplay:
    """Tests for costs display in settings."""

    def test_costs_section_visible(self, authenticated_page: Page):
        """Costs section should display session, 7-day, and monthly costs."""
        page = authenticated_page

        # Navigate to settings
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-settings"]').click()

        # Wait for settings content
        expect(page.locator('[data-testid="settings-content"]')).to_be_visible(timeout=5000)

        # Check for cost elements
        expect(page.locator('[data-testid="costs-session"]')).to_be_visible()
        expect(page.locator('[data-testid="costs-seven-days"]')).to_be_visible()
        expect(page.locator('[data-testid="costs-month"]')).to_be_visible()


class TestProviderSelect:
    """Tests for LLM provider selection."""

    def test_provider_select_visible(self, authenticated_page: Page):
        """Provider select should be visible in LLMs section."""
        page = authenticated_page

        # Navigate to settings
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-settings"]').click()

        # Wait for settings content
        expect(page.locator('[data-testid="settings-content"]')).to_be_visible(timeout=5000)

        # Expand LLMs section if collapsed (click header)
        llms_section = page.get_by_text("LLMs")
        if llms_section.is_visible():
            llms_section.click()

        # Check for provider select
        expect(page.locator('[data-testid="default-provider"]')).to_be_visible(timeout=5000)


class TestBudgetInput:
    """Tests for budget input fields."""

    def test_budget_input_visible(self, authenticated_page: Page):
        """Budget input fields should be visible."""
        page = authenticated_page

        # Navigate to settings
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-settings"]').click()

        # Wait for settings content
        expect(page.locator('[data-testid="settings-content"]')).to_be_visible(timeout=5000)

        # Expand LLMs section if collapsed
        llms_section = page.get_by_text("LLMs")
        if llms_section.is_visible():
            llms_section.click()

        # Check for budget inputs
        expect(page.locator('[data-testid="budget-limit"]')).to_be_visible(timeout=5000)
        expect(page.locator('[data-testid="budget-period"]')).to_be_visible(timeout=5000)


class TestFreshStart:
    """Tests for fresh start functionality."""

    def test_fresh_start_button_visible(self, authenticated_page: Page):
        """Fresh start button should be visible in settings."""
        page = authenticated_page

        # Navigate to settings
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-settings"]').click()

        # Wait for settings content
        expect(page.locator('[data-testid="settings-content"]')).to_be_visible(timeout=5000)

        # Expand Fresh Start section
        fresh_start_section = page.get_by_text("Fresh Start")
        if fresh_start_section.is_visible():
            fresh_start_section.click()

        # Check for fresh start button
        expect(page.locator('[data-testid="fresh-start-btn"]')).to_be_visible(timeout=5000)


class TestBackups:
    """Tests for backups functionality."""

    def test_backups_list_visible(self, authenticated_page: Page):
        """Backups list should be visible when section is expanded."""
        page = authenticated_page

        # Navigate to settings
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-settings"]').click()

        # Wait for settings content
        expect(page.locator('[data-testid="settings-content"]')).to_be_visible(timeout=5000)

        # Expand Backups section
        backups_section = page.get_by_text("Backups")
        if backups_section.is_visible():
            backups_section.click()

        # Check for backups list
        expect(page.locator('[data-testid="backups-list"]')).to_be_visible(timeout=5000)
