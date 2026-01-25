"""E2E tests for Focus tab functionality."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


class TestFocusTabLoads:
    """Tests for Focus tab loading."""

    def test_focus_tab_loads(self, authenticated_page: Page):
        """Focus tab should load and show content."""
        page = authenticated_page
        expect(page.locator('[data-testid="tab-focus"]')).to_be_visible()
        expect(page.locator('[data-testid="focus-content"]')).to_be_visible()

    def test_today_section_visible(self, authenticated_page: Page):
        """Today section should be visible on Focus tab."""
        page = authenticated_page
        expect(page.locator('[data-testid="today-section"]')).to_be_visible(timeout=5000)


class TestTimelineNavigation:
    """Tests for navigating between timeline views."""

    def _expand_timelines_section(self, page: Page):
        """Helper to expand the Timelines section if collapsed."""
        section = page.locator('[data-testid="section-timelines"]')
        section.scroll_into_view_if_needed()
        # Check if section is collapsed (doesn't have 'open' class)
        if "open" not in (section.get_attribute("class") or ""):
            section.click()
            # Wait for the section to expand
            page.wait_for_timeout(300)

    def test_navigate_to_upcoming(self, authenticated_page: Page):
        """Should be able to navigate to Upcoming timeline."""
        page = authenticated_page
        self._expand_timelines_section(page)
        page.locator('[data-testid="menu-upcoming"]').click()
        expect(page.locator('[data-testid="back-btn"]')).to_be_visible(timeout=5000)

    def test_navigate_to_anytime(self, authenticated_page: Page):
        """Should be able to navigate to Anytime timeline."""
        page = authenticated_page
        self._expand_timelines_section(page)
        page.locator('[data-testid="menu-anytime"]').click()
        expect(page.locator('[data-testid="back-btn"]')).to_be_visible(timeout=5000)

    def test_navigate_to_someday(self, authenticated_page: Page):
        """Should be able to navigate to Someday timeline."""
        page = authenticated_page
        self._expand_timelines_section(page)
        page.locator('[data-testid="menu-someday"]').click()
        expect(page.locator('[data-testid="back-btn"]')).to_be_visible(timeout=5000)

    def test_navigate_to_completed(self, authenticated_page: Page):
        """Should be able to navigate to Completed topics."""
        page = authenticated_page
        self._expand_timelines_section(page)
        page.locator('[data-testid="menu-completed"]').click()
        expect(page.locator('[data-testid="back-btn"]')).to_be_visible(timeout=5000)


class TestQuickAdd:
    """Tests for quick add topicfunctionality."""

    def test_quick_add_elements_visible(self, authenticated_page: Page):
        """Quick add input and button should be visible."""
        page = authenticated_page
        expect(page.locator('[data-testid="context-input"]')).to_be_visible()
        expect(page.locator('[data-testid="quick-add-btn"]')).to_be_visible()


class TestTopicCard:
    """Tests for topiccard interactions."""

    def test_topic_card_opens_detail(self, authenticated_page: Page):
        """Clicking a topiccard should open topicdetail view."""
        page = authenticated_page

        # First check if there are any topiccards
        topic_cards = page.locator('[data-testid="topic-card"]')
        if topic_cards.count() > 0:
            # Click the first topiccard
            topic_cards.first.click()

            # Should show topicdetail view with back button
            expect(page.locator('[data-testid="back-btn"]')).to_be_visible(timeout=5000)
            expect(page.locator('[data-testid="topic-detail"]')).to_be_visible(timeout=5000)


class TestTopicDetail:
    """Tests for topicdetail view elements."""

    def test_topic_detail_elements(self, authenticated_page: Page):
        """Topic detail should show name and description sections."""
        page = authenticated_page

        # Navigate to a topicif one exists
        topic_cards = page.locator('[data-testid="topic-card"]')
        if topic_cards.count() > 0:
            topic_cards.first.click()

            # Wait for detail view
            expect(page.locator('[data-testid="topic-detail"]')).to_be_visible(timeout=5000)

            # Check for name and description sections
            expect(page.locator('[data-testid="topic-name"]')).to_be_visible()
            expect(page.locator('[data-testid="topic-description"]')).to_be_visible()
