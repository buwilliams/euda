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

    def test_voice_button_visible(self, authenticated_page: Page):
        """Voice button should be visible."""
        page = authenticated_page

        expect(page.locator('[data-testid="voice-btn"]')).to_be_visible()


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
        expect(page.locator('[data-testid="message-user"]')).to_be_visible(timeout=5000)

    def test_send_message_shows_thinking(self, authenticated_page: Page):
        """Sending a message should show thinking indicator."""
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Type and send a message
        page.locator('[data-testid="context-input"]').fill("Test thinking indicator")
        page.locator('[data-testid="send-btn"]').click()

        # Thinking indicator should appear (may be brief)
        # Note: This may be flaky if response is very fast
        expect(page.locator('[data-testid="thinking-indicator"]')).to_be_visible(timeout=2000)


class TestReceiveResponse:
    """Tests for receiving agent responses."""

    def test_receive_agent_response(self, authenticated_page: Page):
        """Should receive an agent response after sending message."""
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Type and send a message
        page.locator('[data-testid="context-input"]').fill("Hello")
        page.locator('[data-testid="send-btn"]').click()

        # Agent response should appear
        expect(page.locator('[data-testid="message-agent"]')).to_be_visible(timeout=30000)
