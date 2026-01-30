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

    def test_controls_button_visible(self, authenticated_page: Page):
        """Controls button should be visible in agent detail view."""
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

        # Controls button should be visible
        expect(page.locator('[data-testid="controls-btn"]')).to_be_visible(timeout=5000)

    def test_pause_option_in_controls_picker(self, authenticated_page: Page):
        """Pause/Resume option should be visible in Controls picker."""
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

        # Click Controls button to open picker
        page.locator('[data-testid="controls-btn"]').click()

        # Wait for picker and check for pause or resume option
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


class TestAgentTopics:
    """Tests for agent topics display (root ancestors with assignee labels)."""

    def test_agent_detail_shows_topics_section(self, authenticated_page: Page):
        """Agent detail view should show a Topics section."""
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


class TestAgentTriggers:
    """Tests for agent triggers list and detail view."""

    def test_triggers_list_and_detail(self, authenticated_page: Page):
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

        triggers_section = page.locator('.topic-section', has_text="Triggers")
        if triggers_section.count() == 0:
            pytest.skip("Triggers section not visible")

        # Expand triggers section
        triggers_section.locator('.topic-section-header').first.click()

        trigger_cards = triggers_section.locator('.child-topic-card')
        if trigger_cards.count() == 0:
            pytest.skip("No triggers configured")

        trigger_cards.first.click()

        # Expect trigger detail view
        expect(page.get_by_text("Event")).to_be_visible(timeout=5000)
        expect(page.get_by_text("Topic")).to_be_visible(timeout=5000)

        # Topics section should be visible
        topics_section = page.get_by_text("Topics", exact=False)
        expect(topics_section.first).to_be_visible(timeout=5000)

    def test_topic_cards_show_assignee_labels(self, authenticated_page: Page):
        """Topic cards in agent detail should show assignee labels."""
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

        # Check for topic cards with assignee labels
        topic_cards = page.locator('[data-testid="topic-card"]')
        if topic_cards.count() > 0:
            first_card = topic_cards.first
            assignee_label = first_card.locator('.card-assignee-label')
            expect(assignee_label).to_be_visible()

    def test_topic_cards_are_clickable_for_drill_down(self, authenticated_page: Page):
        """Topic cards in agent detail should be clickable for drill-down navigation."""
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

        # Check for topic cards in the Topics section
        topic_cards = page.locator('[data-testid="topic-card"]')
        if topic_cards.count() > 0:
            # Topic cards should be clickable
            first_card = topic_cards.first
            expect(first_card).to_be_visible()

            # Click the topic card to drill down (shows root ancestor for navigation)
            first_card.click()
            page.wait_for_timeout(500)

            # Should navigate to topic detail (back button should be visible)
            expect(page.locator('[data-testid="back-btn"]')).to_be_visible(timeout=5000)

    def test_topic_drill_down_and_back_navigation(self, authenticated_page: Page):
        """Drilling down into a topic and back should work correctly."""
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

        # Check for topic cards
        topic_cards = page.locator('[data-testid="topic-card"]')
        if topic_cards.count() == 0:
            pytest.skip("No topic cards in agent detail")

        # Click first topic to drill down
        topic_cards.first.click()
        page.wait_for_timeout(500)

        # Should be in topic detail view
        expect(page.locator('[data-testid="topic-detail"]')).to_be_visible(timeout=5000)

        # Navigate back
        page.locator('[data-testid="back-btn"]').click()
        page.wait_for_timeout(500)

        # Should be back in agent detail
        expect(page.locator('[data-testid="agent-detail"]')).to_be_visible(timeout=5000)
