"""E2E tests for navigation functionality."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


class TestTabSwitching:
    """Tests for switching between main tabs."""

    def test_switch_to_focus_tab(self, authenticated_page: Page):
        """Should be able to switch to Focus tab."""
        page = authenticated_page

        # Click Focus tab button
        page.locator('[data-testid="tab-btn-focus"]').click()

        # Focus tab should be visible
        expect(page.locator('[data-testid="tab-focus"]')).to_be_visible()
        expect(page.locator('[data-testid="focus-content"]')).to_be_visible()

    def test_switch_to_chat_tab(self, authenticated_page: Page):
        """Should be able to switch to Chat tab."""
        page = authenticated_page

        # Click Chat tab button
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Chat tab should be visible
        expect(page.locator('[data-testid="tab-chat"]')).to_be_visible()
        expect(page.locator('[data-testid="inline-messages"]')).to_be_visible()


class TestOverflowMenu:
    """Tests for overflow menu functionality."""

    def test_overflow_menu_opens(self, authenticated_page: Page):
        """Clicking overflow button should open the menu."""
        page = authenticated_page

        # Click overflow button
        page.locator('[data-testid="overflow-btn"]').click()

        # Overflow menu should be visible
        expect(page.locator('[data-testid="overflow-menu"]')).to_be_visible()

    def test_overflow_menu_items_visible(self, authenticated_page: Page):
        """Overflow menu should show all menu items."""
        page = authenticated_page

        # Click overflow button
        page.locator('[data-testid="overflow-btn"]').click()

        # Check for menu items
        expect(page.locator('[data-testid="overflow-about"]')).to_be_visible()
        expect(page.locator('[data-testid="overflow-settings"]')).to_be_visible()
        expect(page.locator('[data-testid="overflow-history"]')).to_be_visible()


class TestMoreMenuNavigation:
    """Tests for navigating through More menu screens."""

    def test_navigate_to_about(self, authenticated_page: Page):
        """Should be able to navigate to About screen."""
        page = authenticated_page

        # Open overflow menu
        page.locator('[data-testid="overflow-btn"]').click()

        # Click About
        page.locator('[data-testid="overflow-about"]').click()

        # About tab should be visible
        expect(page.locator('[data-testid="tab-about"]')).to_be_visible()

    def test_navigate_to_settings(self, authenticated_page: Page):
        """Should be able to navigate to Settings screen."""
        page = authenticated_page

        # Open overflow menu
        page.locator('[data-testid="overflow-btn"]').click()

        # Click Settings
        page.locator('[data-testid="overflow-settings"]').click()

        # Settings tab should be visible
        expect(page.locator('[data-testid="tab-settings"]')).to_be_visible()

    def test_navigate_to_history(self, authenticated_page: Page):
        """Should be able to navigate to History screen."""
        page = authenticated_page

        # Open overflow menu
        page.locator('[data-testid="overflow-btn"]').click()

        # Click History
        page.locator('[data-testid="overflow-history"]').click()

        # History tab should be visible
        expect(page.locator('[data-testid="tab-history"]')).to_be_visible()


class TestBackNavigation:
    """Tests for back navigation."""

    def _expand_timelines_section(self, page: Page):
        """Helper to expand the Timelines section if collapsed."""
        section = page.locator('[data-testid="section-timelines"]')
        section.scroll_into_view_if_needed()
        # Check if section is collapsed (doesn't have 'open' class)
        if "open" not in (section.get_attribute("class") or ""):
            section.click()
            # Wait for the section to expand
            page.wait_for_timeout(300)

    def test_back_button_returns_to_previous(self, authenticated_page: Page):
        """Back button should return to previous view."""
        page = authenticated_page

        # Expand Timelines section and navigate to upcoming
        self._expand_timelines_section(page)
        page.locator('[data-testid="menu-upcoming"]').click()

        # Back button should be visible
        expect(page.locator('[data-testid="back-btn"]')).to_be_visible(timeout=5000)

        # Click back button
        page.locator('[data-testid="back-btn"]').click()

        # Should return to Focus menu (today section visible)
        expect(page.locator('[data-testid="today-section"]')).to_be_visible(timeout=5000)

    def test_nested_back_navigation(self, authenticated_page: Page):
        """Back button should work through multiple navigation levels."""
        page = authenticated_page

        # Expand Timelines section and navigate to upcoming
        self._expand_timelines_section(page)
        page.locator('[data-testid="menu-upcoming"]').click()
        expect(page.locator('[data-testid="back-btn"]')).to_be_visible(timeout=5000)

        # If there are jobs, navigate into one
        job_cards = page.locator('[data-testid="job-card"]')
        if job_cards.count() > 0:
            job_cards.first.click()

            # Wait for job detail
            expect(page.locator('[data-testid="job-detail"]')).to_be_visible(timeout=5000)

            # Go back
            page.locator('[data-testid="back-btn"]').click()

            # Should be back at upcoming view (back button still visible)
            expect(page.locator('[data-testid="back-btn"]')).to_be_visible(timeout=5000)

            # Go back again
            page.locator('[data-testid="back-btn"]').click()

            # Should be back at Focus menu
            expect(page.locator('[data-testid="today-section"]')).to_be_visible(timeout=5000)
