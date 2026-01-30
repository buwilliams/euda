"""E2E tests for History tab functionality."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


class TestHistoryTabLoads:
    """Tests for History tab loading."""

    def test_history_tab_loads(self, authenticated_page: Page):
        """History tab should load when navigated to."""
        page = authenticated_page

        # Open overflow menu and navigate to history
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-history"]').click()

        expect(page.locator('[data-testid="tab-history"]')).to_be_visible()
        expect(page.locator('[data-testid="history-content"]')).to_be_visible()


class TestHistoryList:
    """Tests for history list display."""

    def test_history_list_visible(self, authenticated_page: Page):
        """History list should be visible."""
        page = authenticated_page

        # Navigate to history
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-history"]').click()

        # Wait for history content to load
        expect(page.locator('[data-testid="history-list"]')).to_be_visible(timeout=5000)


class TestHistoryCard:
    """Tests for history card interactions."""

    def test_history_card_opens_detail(self, authenticated_page: Page):
        """Clicking a history card should open detail view."""
        page = authenticated_page

        # Navigate to history
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-history"]').click()

        # Wait for history content
        expect(page.locator('[data-testid="history-list"]')).to_be_visible(timeout=5000)

        # Check if there are any history cards
        history_cards = page.locator('[data-testid="history-card"]')
        if history_cards.count() > 0:
            # Click the first history card
            history_cards.first.click()

            # Should show history detail view
            expect(page.locator('[data-testid="history-detail"]')).to_be_visible(timeout=5000)


class TestHistoryDetail:
    """Tests for history detail view."""

    def test_history_detail_buttons(self, authenticated_page: Page):
        """History detail should have continue and delete buttons."""
        page = authenticated_page

        # Navigate to history
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-history"]').click()

        # Wait for history content
        expect(page.locator('[data-testid="history-list"]')).to_be_visible(timeout=5000)

        # Open first history card if available
        history_cards = page.locator('[data-testid="history-card"]')
        if history_cards.count() > 0:
            history_cards.first.click()

            # Wait for detail view
            expect(page.locator('[data-testid="history-detail"]')).to_be_visible(timeout=5000)

            # Check for action buttons
            expect(page.locator('[data-testid="continue-btn"]')).to_be_visible()
            expect(page.locator('[data-testid="delete-btn"]')).to_be_visible()

            # Transcript container should be visible
            expect(page.locator('.prompt-messages-list')).to_be_visible(timeout=5000)


class TestHistoryTopicMode:
    """Tests for topic history and @topic mode restoration."""

    def test_topic_history_card_shows_label(self, authenticated_page: Page):
        page = authenticated_page

        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-history"]').click()

        expect(page.locator('[data-testid="history-list"]')).to_be_visible(timeout=5000)

        topic_labels = page.locator('.history-topic-label')
        if topic_labels.count() == 0:
            pytest.skip("No topic conversations in history")

        label_text = topic_labels.first.inner_text()
        assert "@topic" in label_text

    def test_topic_history_continue_restores_topic_mode(self, authenticated_page: Page):
        page = authenticated_page

        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-history"]').click()

        expect(page.locator('[data-testid="history-list"]')).to_be_visible(timeout=5000)

        # Open first topic-labeled conversation
        topic_cards = page.locator('[data-testid="history-card"]').filter(has=page.locator('.history-topic-label'))
        if topic_cards.count() == 0:
            pytest.skip("No topic conversations in history")

        topic_cards.first.click()
        expect(page.locator('[data-testid="history-detail"]')).to_be_visible(timeout=5000)

        page.locator('[data-testid="continue-btn"]').click()

        # Should be in chat tab with @topic label active
        expect(page.locator('#topic-context-label')).to_contain_text('@topic', timeout=5000)
