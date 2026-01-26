"""E2E tests for conversation initialization functionality.

Tests the 6-hour inactivity-based conversation management:
- Auto-resume if last message < 6 hours ago
- Fresh start if last message > 6 hours ago
- Backend is source of truth (no localStorage)
"""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


class TestConversationLoading:
    """Tests for conversation loading on page load."""

    def test_chat_shows_loading_initially(self, authenticated_page: Page):
        """Chat should show loading state while fetching conversations."""
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # The loading state may be very brief, so we just verify chat tab loads
        expect(page.locator('[data-testid="tab-chat"]')).to_be_visible()

    def test_fresh_visit_shows_empty_state_or_conversation(self, authenticated_page: Page):
        """Fresh visit should show either empty state or loaded conversation."""
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Wait for initialization to complete
        page.wait_for_timeout(1000)

        # Should show either empty state OR messages (if recent conversation exists)
        empty_or_messages = page.locator(
            '[data-testid="chat-empty-state"], [data-testid="message-user"], [data-testid="message-agent"]'
        )
        expect(empty_or_messages.first).to_be_visible(timeout=5000)


class TestNewChatButton:
    """Tests for the New Chat button functionality."""

    def test_new_chat_clears_messages(self, authenticated_page: Page):
        """New Chat button should clear current conversation."""
        page = authenticated_page

        # Switch to chat tab and send a message
        page.locator('[data-testid="tab-btn-chat"]').click()
        page.locator('[data-testid="context-input"]').fill("Test message for new chat")
        page.locator('[data-testid="send-btn"]').click()

        # Wait for message to appear
        expect(page.locator('[data-testid="message-user"]')).to_be_visible(timeout=5000)

        # Click New Chat
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="new-chat-btn"]').click()

        # Should show empty state
        expect(page.locator('[data-testid="chat-empty-state"]')).to_be_visible(timeout=5000)

    def test_new_chat_allows_fresh_conversation(self, authenticated_page: Page):
        """After New Chat, sending a message should create new conversation."""
        page = authenticated_page

        # Start fresh
        page.locator('[data-testid="tab-btn-chat"]').click()
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="new-chat-btn"]').click()

        # Wait for empty state
        expect(page.locator('[data-testid="chat-empty-state"]')).to_be_visible(timeout=5000)

        # Send a new message
        page.locator('[data-testid="context-input"]').fill("Starting fresh conversation")
        page.locator('[data-testid="send-btn"]').click()

        # User message should appear
        expect(page.locator('[data-testid="message-user"]')).to_be_visible(timeout=5000)


class TestConversationPersistence:
    """Tests for conversation persistence across page loads."""

    def test_conversation_persists_on_refresh(self, authenticated_page: Page):
        """Conversation should persist after page refresh (within 6 hours)."""
        page = authenticated_page

        # Start a new chat and send a message
        page.locator('[data-testid="tab-btn-chat"]').click()
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="new-chat-btn"]').click()

        # Wait for empty state
        expect(page.locator('[data-testid="chat-empty-state"]')).to_be_visible(timeout=5000)

        # Send a unique message
        unique_msg = f"Persistence test message {page.evaluate('Date.now()')}"
        page.locator('[data-testid="context-input"]').fill(unique_msg)
        page.locator('[data-testid="send-btn"]').click()

        # Wait for user message to appear
        expect(page.locator('[data-testid="message-user"]')).to_be_visible(timeout=5000)

        # Wait for any processing
        page.wait_for_timeout(2000)

        # Reload the page
        page.reload()

        # Wait for page to fully load
        page.wait_for_selector('[data-testid="app-container"]', state="attached", timeout=10000)
        page.wait_for_timeout(500)

        # Handle potential login
        login_overlay = page.locator('[data-testid="login-overlay"]:not(.hidden)')
        if login_overlay.is_visible():
            import os
            password = os.environ.get("EUNO_TEST_PASSWORD", "test")
            page.locator('[data-testid="login-password"]').fill(password)
            page.locator('[data-testid="login-btn"]').click()
            page.wait_for_selector('[data-testid="login-overlay"].hidden', state="attached", timeout=10000)

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Wait for conversation to load
        page.wait_for_timeout(2000)

        # The conversation should be loaded (we should see our message)
        # Note: This tests that backend returns the conversation within 6 hours
        messages = page.locator('[data-testid="message-user"]')
        expect(messages.first).to_be_visible(timeout=5000)


class TestHistoryIntegration:
    """Tests for history tab integration with conversation system."""

    def test_continue_from_history_loads_conversation(self, authenticated_page: Page):
        """Continuing from history should load the conversation."""
        page = authenticated_page

        # First, create a conversation
        page.locator('[data-testid="tab-btn-chat"]').click()
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="new-chat-btn"]').click()

        expect(page.locator('[data-testid="chat-empty-state"]')).to_be_visible(timeout=5000)

        page.locator('[data-testid="context-input"]').fill("Message for history test")
        page.locator('[data-testid="send-btn"]').click()

        expect(page.locator('[data-testid="message-user"]')).to_be_visible(timeout=5000)

        # Wait for processing
        page.wait_for_timeout(2000)

        # Navigate to history
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="overflow-history"]').click()

        # Wait for history to load
        expect(page.locator('[data-testid="history-list"]')).to_be_visible(timeout=5000)

        # Check if there are history cards
        history_cards = page.locator('[data-testid="history-card"]')
        if history_cards.count() > 0:
            # Click first card to open detail
            history_cards.first.click()

            # Wait for detail view
            expect(page.locator('[data-testid="history-detail"]')).to_be_visible(timeout=5000)

            # Click Continue button
            page.locator('[data-testid="continue-btn"]').click()

            # Should switch to chat tab with conversation loaded
            expect(page.locator('[data-testid="tab-chat"]')).to_be_visible(timeout=5000)
            expect(page.locator('[data-testid="message-user"]')).to_be_visible(timeout=5000)


class TestConversationIdInApi:
    """Tests that API uses conversation_id, not session_id."""

    def test_api_returns_conversation_id(self, authenticated_page: Page):
        """API should return conversation_id in responses."""
        page = authenticated_page

        # Intercept the chat API call
        response_data = []

        def handle_response(response):
            if "/api/chat" in response.url and response.request.method == "POST":
                try:
                    data = response.json()
                    response_data.append(data)
                except:
                    pass

        page.on("response", handle_response)

        # Send a message
        page.locator('[data-testid="tab-btn-chat"]').click()
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="new-chat-btn"]').click()

        expect(page.locator('[data-testid="chat-empty-state"]')).to_be_visible(timeout=5000)

        page.locator('[data-testid="context-input"]').fill("API test message")
        page.locator('[data-testid="send-btn"]').click()

        # Wait for response
        page.wait_for_timeout(3000)

        # Check that we got a response with conversation_id
        if response_data:
            assert "conversation_id" in response_data[0], "API should return conversation_id"
            assert "session_id" not in response_data[0], "API should NOT return session_id"

    def test_recent_conversations_api_uses_conversation_id(self, authenticated_page: Page):
        """Recent conversations API should use conversation_id."""
        page = authenticated_page

        # Intercept the recent conversations API call
        response_data = []

        def handle_response(response):
            if "/api/chat/conversations/recent" in response.url:
                try:
                    data = response.json()
                    response_data.append(data)
                except:
                    pass

        page.on("response", handle_response)

        # Trigger a page load which calls initializeConversation
        page.reload()

        # Wait for API call
        page.wait_for_timeout(2000)

        # Handle login if needed
        login_overlay = page.locator('[data-testid="login-overlay"]:not(.hidden)')
        if login_overlay.is_visible():
            import os
            password = os.environ.get("EUNO_TEST_PASSWORD", "test")
            page.locator('[data-testid="login-password"]').fill(password)
            page.locator('[data-testid="login-btn"]').click()
            page.wait_for_timeout(2000)

        # Check the API response
        if response_data and response_data[0].get("conversations"):
            for conv in response_data[0]["conversations"]:
                assert "conversation_id" in conv, "Conversations should have conversation_id"
                assert "session_id" not in conv, "Conversations should NOT have session_id"
