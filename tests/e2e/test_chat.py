"""E2E tests for Chat tab functionality."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


class TestChatTabLoads:
    """Tests for Chat tab loading."""

    def test_chat_tab_loads(self, authenticated_page: Page):
        """Chat tab should load when clicked."""
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        expect(page.locator('[data-testid="tab-chat"]')).to_be_visible()
        expect(page.locator('[data-testid="inline-messages"]')).to_be_visible()


class TestChatEmptyState:
    """Tests for chat empty state."""

    def test_empty_state_with_greeting(self, authenticated_page: Page):
        """Chat should show empty state with greeting when no messages."""
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Start a new chat to ensure empty state
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="new-chat-btn"]').click()

        # Check for empty state
        expect(page.locator('[data-testid="chat-empty-state"]')).to_be_visible(timeout=5000)


class TestChatInput:
    """Tests for chat input elements."""

    def test_input_elements_visible(self, authenticated_page: Page):
        """Chat input and send button should be visible."""
        page = authenticated_page

        expect(page.locator('[data-testid="context-input"]')).to_be_visible()
        expect(page.locator('[data-testid="send-btn"]')).to_be_visible()

    def test_voice_button_exists(self, authenticated_page: Page):
        """Voice button should exist (may be hidden if STT unavailable)."""
        page = authenticated_page

        # Voice button exists but may be hidden if STT provider not configured
        voice_btn = page.locator('[data-testid="voice-btn"]')
        expect(voice_btn).to_be_attached()


class TestSendMessage:
    """Tests for sending messages."""

    def test_send_message_shows_user_message(self, authenticated_page: Page):
        """Sending a message should show it as a user message."""
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Type and send a message
        page.locator('[data-testid="context-input"]').fill("Hello, this is a test message")
        page.locator('[data-testid="send-btn"]').click()

        # User message should appear
        expect(page.locator('[data-testid="message-user"]').first).to_be_visible(timeout=5000)

    def test_send_message_shows_processing_state(self, authenticated_page: Page):
        """Sending a message should show thinking indicator or agent response."""
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Type and send a message
        page.locator('[data-testid="context-input"]').fill("Test thinking indicator")
        page.locator('[data-testid="send-btn"]').click()

        # Either thinking indicator or agent response should appear
        # (if response is very fast, thinking indicator may already be gone)
        thinking_or_response = page.locator(
            '[data-testid="thinking-indicator"], [data-testid="message-agent"]'
        )
        expect(thinking_or_response.first).to_be_visible(timeout=10000)


class TestReceiveResponse:
    """Tests for receiving agent responses."""

    @pytest.mark.skip(reason="Requires running agent with LLM API - run manually when testing agent responses")
    def test_receive_agent_response(self, authenticated_page: Page):
        """Should receive an agent response after sending message.

        Note: This test requires a running agent with LLM API configured.
        It is skipped by default since agent response time depends on external services.
        """
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Type and send a message
        page.locator('[data-testid="context-input"]').fill("Hello")
        page.locator('[data-testid="send-btn"]').click()

        # Agent response should appear
        expect(page.locator('[data-testid="message-agent"]').first).to_be_visible(timeout=30000)
