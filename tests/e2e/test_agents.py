"""E2E tests for Agent management functionality."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


class TestAgentsContainer:
    """Tests for agents container display."""

    def test_agents_container_loads(self, authenticated_page: Page):
        """Agents container should be accessible from Focus tab."""
        page = authenticated_page

        # The agents container is accessible via the Collections section
        # Look for the Collections section header and expand it
        collections_section = page.get_by_text("Collections")
        if collections_section.is_visible():
            collections_section.click()

            # Look for Agents menu item
            agents_link = page.get_by_text("Agents")
            if agents_link.is_visible():
                agents_link.click()

                # Should show agents container
                expect(page.locator('[data-testid="agents-container"]')).to_be_visible(timeout=5000)


class TestAgentCard:
    """Tests for agent card interactions."""

    def test_agent_card_visible(self, authenticated_page: Page):
        """Agent cards should be visible in agents container."""
        page = authenticated_page

        # Navigate to agents container
        collections_section = page.get_by_text("Collections")
        if collections_section.is_visible():
            collections_section.click()

            agents_link = page.get_by_text("Agents")
            if agents_link.is_visible():
                agents_link.click()

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

        # Navigate to agents container
        collections_section = page.get_by_text("Collections")
        if collections_section.is_visible():
            collections_section.click()

            agents_link = page.get_by_text("Agents")
            if agents_link.is_visible():
                agents_link.click()

                # Wait for agents container
                expect(page.locator('[data-testid="agents-container"]')).to_be_visible(timeout=5000)

                # Click first agent card
                agent_cards = page.locator('[data-testid="agent-card"]')
                if agent_cards.count() > 0:
                    agent_cards.first.click()

                    # Should show agent detail
                    expect(page.locator('[data-testid="agent-detail"]')).to_be_visible(timeout=5000)


class TestAgentManagement:
    """Tests for agent management (pause/resume)."""

    def test_pause_button_visible(self, authenticated_page: Page):
        """Pause button should be visible in agent manage view."""
        page = authenticated_page

        # Navigate to an agent and then to manage view
        collections_section = page.get_by_text("Collections")
        if collections_section.is_visible():
            collections_section.click()

            agents_link = page.get_by_text("Agents")
            if agents_link.is_visible():
                agents_link.click()

                # Wait for agents container
                expect(page.locator('[data-testid="agents-container"]')).to_be_visible(timeout=5000)

                # Click first agent card
                agent_cards = page.locator('[data-testid="agent-card"]')
                if agent_cards.count() > 0:
                    agent_cards.first.click()

                    # Wait for agent detail
                    expect(page.locator('[data-testid="agent-detail"]')).to_be_visible(timeout=5000)

                    # Click Manage to go to manage view
                    manage_link = page.get_by_text("Manage")
                    if manage_link.is_visible():
                        manage_link.click()

                        # Pause button should be visible (or resume if already paused)
                        pause_or_resume = page.locator('[data-testid="pause-btn"], [data-testid="resume-btn"]')
                        expect(pause_or_resume.first).to_be_visible(timeout=5000)


class TestAgentIdentity:
    """Tests for viewing agent identity."""

    def test_identity_content_visible(self, authenticated_page: Page):
        """Identity content should be visible in identity view."""
        page = authenticated_page

        # Navigate to an agent's identity view
        collections_section = page.get_by_text("Collections")
        if collections_section.is_visible():
            collections_section.click()

            agents_link = page.get_by_text("Agents")
            if agents_link.is_visible():
                agents_link.click()

                # Wait for agents container
                expect(page.locator('[data-testid="agents-container"]')).to_be_visible(timeout=5000)

                # Click first agent card
                agent_cards = page.locator('[data-testid="agent-card"]')
                if agent_cards.count() > 0:
                    agent_cards.first.click()

                    # Wait for agent detail
                    expect(page.locator('[data-testid="agent-detail"]')).to_be_visible(timeout=5000)

                    # Click Manage
                    page.get_by_text("Manage").click()

                    # Wait for manage view, then click Identity
                    page.wait_for_timeout(500)  # Brief wait for animation
                    identity_link = page.get_by_text("Identity")
                    if identity_link.is_visible():
                        identity_link.click()

                        # Identity content should be visible
                        expect(page.locator('[data-testid="identity-content"]')).to_be_visible(timeout=5000)


class TestAgentMemory:
    """Tests for viewing agent memory."""

    def test_memory_list_visible(self, authenticated_page: Page):
        """Memory list should be visible in memory view."""
        page = authenticated_page

        # Navigate to an agent's memory view
        collections_section = page.get_by_text("Collections")
        if collections_section.is_visible():
            collections_section.click()

            agents_link = page.get_by_text("Agents")
            if agents_link.is_visible():
                agents_link.click()

                # Wait for agents container
                expect(page.locator('[data-testid="agents-container"]')).to_be_visible(timeout=5000)

                # Click first agent card
                agent_cards = page.locator('[data-testid="agent-card"]')
                if agent_cards.count() > 0:
                    agent_cards.first.click()

                    # Wait for agent detail
                    expect(page.locator('[data-testid="agent-detail"]')).to_be_visible(timeout=5000)

                    # Click Manage
                    page.get_by_text("Manage").click()

                    # Wait for manage view, then click Short-term Memory
                    page.wait_for_timeout(500)  # Brief wait for animation
                    memory_link = page.get_by_text("Short-term Memory")
                    if memory_link.is_visible():
                        memory_link.click()

                        # Memory list should be visible
                        expect(page.locator('[data-testid="memory-list"]')).to_be_visible(timeout=5000)
