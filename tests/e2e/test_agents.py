"""E2E tests for Agent management functionality."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def navigate_to_agents(page: Page):
    """Navigate to agents container via Collections > Agents."""
    # First, ensure we're on the Focus tab
    focus_tab = page.locator('[data-testid="tab-btn-focus"]')
    focus_tab.click()
    page.wait_for_timeout(500)

    # The agents container is accessible via the Collections section
    collections_section = page.get_by_text("Collections", exact=True)
    expect(collections_section).to_be_visible(timeout=5000)
    collections_section.click()

    # Wait for collapsible content to expand
    page.wait_for_timeout(300)

    # Click Agents menu item
    agents_link = page.locator('.focus-menu-item:has-text("Agents")')
    expect(agents_link).to_be_visible(timeout=2000)
    agents_link.click()

    # Wait for view transition animation to complete
    page.wait_for_timeout(500)


class TestAgentsContainer:
    """Tests for agents container display."""

    def test_agents_container_loads(self, authenticated_page: Page):
        """Agents container should be accessible from Focus tab."""
        page = authenticated_page

        navigate_to_agents(page)

        # Should show agents container
        expect(page.locator('[data-testid="agents-container"]')).to_be_visible(timeout=5000)


class TestAgentCard:
    """Tests for agent card interactions."""

    def test_agent_card_visible(self, authenticated_page: Page):
        """Agent cards should be visible in agents container."""
        page = authenticated_page

        navigate_to_agents(page)

        # Wait for agents container
        expect(page.locator('[data-testid="agents-container"]')).to_be_visible(timeout=5000)

        # Check for agent cards
        agent_cards = page.locator('[data-testid="agent-card"]')
        if agent_cards.count() > 0:
            expect(agent_cards.first).to_be_visible()


class TestAgentDetail:
    """Tests for agent detail view."""

    def test_agent_detail_view(self, authenticated_page: Page):
        """Clicking an agent card should open agent detail view."""
        page = authenticated_page

        navigate_to_agents(page)

        # Wait for agents container
        expect(page.locator('[data-testid="agents-container"]')).to_be_visible(timeout=5000)

        # Click first agent card
        agent_cards = page.locator('[data-testid="agent-card"]')
        if agent_cards.count() == 0:
            pytest.skip("No agent cards available")

        agent_cards.first.click()

        # Should show agent detail
        expect(page.locator('[data-testid="agent-detail"]')).to_be_visible(timeout=5000)


class TestAgentManagement:
    """Tests for agent management (pause/resume)."""

    def test_pause_button_visible(self, authenticated_page: Page):
        """Pause button should be visible in agent detail view."""
        page = authenticated_page

        navigate_to_agents(page)

        # Wait for agents container
        expect(page.locator('[data-testid="agents-container"]')).to_be_visible(timeout=5000)

        # Click first agent card
        agent_cards = page.locator('[data-testid="agent-card"]')
        if agent_cards.count() == 0:
            pytest.skip("No agent cards available")

        agent_cards.first.click()

        # Wait for agent detail
        expect(page.locator('[data-testid="agent-detail"]')).to_be_visible(timeout=5000)

        # Pause button should be visible in detail view (or resume if already paused)
        pause_or_resume = page.locator('[data-testid="pause-btn"], [data-testid="resume-btn"]')
        expect(pause_or_resume.first).to_be_visible(timeout=5000)


class TestAgentIdentity:
    """Tests for viewing agent identity."""

    def test_identity_content_visible(self, authenticated_page: Page):
        """Identity content should be visible in identity view."""
        page = authenticated_page

        navigate_to_agents(page)

        # Wait for agents container
        expect(page.locator('[data-testid="agents-container"]')).to_be_visible(timeout=5000)

        # Click first agent card
        agent_cards = page.locator('[data-testid="agent-card"]')
        if agent_cards.count() == 0:
            pytest.skip("No agent cards available")

        agent_cards.first.click()

        # Wait for agent detail
        expect(page.locator('[data-testid="agent-detail"]')).to_be_visible(timeout=5000)

        # Click Identity section (now directly in agent detail view)
        identity_link = page.get_by_text("Identity")
        if not identity_link.is_visible(timeout=2000):
            pytest.skip("Identity link not visible")

        identity_link.click()

        # Identity content should be visible
        expect(page.locator('[data-testid="identity-content"]')).to_be_visible(timeout=5000)


class TestAgentMemory:
    """Tests for viewing agent memory."""

    def test_memory_list_visible(self, authenticated_page: Page):
        """Memory list should be visible in memory view."""
        page = authenticated_page

        navigate_to_agents(page)

        # Wait for agents container
        expect(page.locator('[data-testid="agents-container"]')).to_be_visible(timeout=5000)

        # Click first agent card
        agent_cards = page.locator('[data-testid="agent-card"]')
        if agent_cards.count() == 0:
            pytest.skip("No agent cards available")

        agent_cards.first.click()

        # Wait for agent detail
        expect(page.locator('[data-testid="agent-detail"]')).to_be_visible(timeout=5000)

        # Click Short-term Memory section (now directly in agent detail view)
        memory_link = page.get_by_text("Short-term Memory")
        if not memory_link.is_visible(timeout=2000):
            pytest.skip("Short-term Memory link not visible")

        memory_link.click()

        # Memory list should be visible
        expect(page.locator('[data-testid="memory-list"]')).to_be_visible(timeout=5000)
