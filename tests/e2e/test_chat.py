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


class TestChatExploration:
    """Tests for chat exploration vs action behavior.

    Spec: data/agents/user/prompts/topic_assignment.md - Recognizing Work Type section.
    Chat should distinguish exploration signals from action signals.
    """

    def test_exploration_message_displays(self, authenticated_page: Page):
        """Exploration-style message should display correctly.

        Tests that exploration signals like "I've been thinking about..."
        are sent and displayed in the chat UI.
        """
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Start a new chat to ensure clean state
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="new-chat-btn"]').click()
        page.wait_for_timeout(500)

        # Type an exploration message
        exploration_message = "I've been thinking about learning philosophy lately"
        page.locator('[data-testid="context-input"]').fill(exploration_message)
        page.locator('[data-testid="send-btn"]').click()

        # User message should appear with the exploration text
        user_message = page.locator('[data-testid="message-user"]').first
        expect(user_message).to_be_visible(timeout=5000)
        expect(user_message).to_contain_text("thinking about")

    def test_action_message_displays(self, authenticated_page: Page):
        """Action-style message should display correctly.

        Tests that action signals like "I need to..." are sent and
        displayed in the chat UI.
        """
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Start a new chat
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="new-chat-btn"]').click()
        page.wait_for_timeout(500)

        # Type an action message
        action_message = "I need to buy groceries tomorrow"
        page.locator('[data-testid="context-input"]').fill(action_message)
        page.locator('[data-testid="send-btn"]').click()

        # User message should appear with the action text
        user_message = page.locator('[data-testid="message-user"]').first
        expect(user_message).to_be_visible(timeout=5000)
        expect(user_message).to_contain_text("need to")

    @pytest.mark.skip(reason="Requires running agent with LLM API - run manually to verify exploration behavior")
    def test_exploration_gets_conversational_response(self, authenticated_page: Page):
        """Exploration message should get a conversational response, not create a topic.

        Spec: When user is exploring an idea, Chat should engage thoughtfully
        and not immediately create a topic or action plan.

        Note: This test requires a running agent with LLM API configured.
        Run manually with: uv run pytest tests/e2e/test_chat.py::TestChatExploration::test_exploration_gets_conversational_response -v --no-header -rN
        """
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Start a new chat
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="new-chat-btn"]').click()
        page.wait_for_timeout(500)

        # Send exploration message
        page.locator('[data-testid="context-input"]').fill(
            "I've been thinking about whether rationality is always the best approach to decision-making"
        )
        page.locator('[data-testid="send-btn"]').click()

        # Wait for agent response
        agent_response = page.locator('[data-testid="message-agent"]').first
        expect(agent_response).to_be_visible(timeout=60000)

        # Navigate to topics to verify no topic was created
        page.locator('[data-testid="tab-btn-topics"]').click()
        page.wait_for_timeout(1000)

        # Check that no topic about "rationality" was created
        # (This is a heuristic - the topic list shouldn't contain the exploration topic)
        topics_container = page.locator('[data-testid="topic-list"], [data-testid="topics-container"]')
        if topics_container.is_visible():
            # If there are topics, none should be about our exploration
            topic_texts = topics_container.inner_text()
            # A conversational exploration shouldn't create a task
            assert "rationality" not in topic_texts.lower() or "thinking about" not in topic_texts.lower()

    @pytest.mark.skip(reason="Requires running agent with LLM API - run manually to verify action behavior")
    def test_action_may_create_topic(self, authenticated_page: Page):
        """Action message may result in topic creation.

        Spec: When user mentions something to track or accomplish,
        Chat creates a topic.

        Note: This test requires a running agent with LLM API configured.
        Run manually with: uv run pytest tests/e2e/test_chat.py::TestChatExploration::test_action_may_create_topic -v --no-header -rN
        """
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Start a new chat
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="new-chat-btn"]').click()
        page.wait_for_timeout(500)

        # Send action message with clear task intent
        unique_task = "buy milk and eggs for breakfast tomorrow morning"
        page.locator('[data-testid="context-input"]').fill(f"I need to {unique_task}")
        page.locator('[data-testid="send-btn"]').click()

        # Wait for agent response
        agent_response = page.locator('[data-testid="message-agent"]').first
        expect(agent_response).to_be_visible(timeout=60000)

        # Navigate to topics
        page.locator('[data-testid="tab-btn-topics"]').click()
        page.wait_for_timeout(1000)

        # Check that a topic was likely created (contains task-related words)
        topics_container = page.locator('[data-testid="topic-list"], [data-testid="topics-container"]')
        if topics_container.is_visible():
            topic_texts = topics_container.inner_text().lower()
            # Action messages should result in topic creation
            assert "milk" in topic_texts or "eggs" in topic_texts or "grocery" in topic_texts or "buy" in topic_texts

    @pytest.mark.skip(reason="Requires running agent with LLM API - run manually to verify exploration flow")
    def test_exploration_to_action_flow(self, authenticated_page: Page):
        """User can explore, then explicitly request tracking.

        Spec: If the idea has legs, ask: "Would you like me to track this somewhere?"
        Only route to tracking if user signals they want ongoing tracking.

        Note: This test requires a running agent with LLM API configured.
        """
        page = authenticated_page

        # Switch to chat tab
        page.locator('[data-testid="tab-btn-chat"]').click()

        # Start a new chat
        page.locator('[data-testid="overflow-btn"]').click()
        page.locator('[data-testid="new-chat-btn"]').click()
        page.wait_for_timeout(500)

        # First: exploration message
        page.locator('[data-testid="context-input"]').fill(
            "I've been thinking about starting a meditation practice"
        )
        page.locator('[data-testid="send-btn"]').click()

        # Wait for conversational response
        expect(page.locator('[data-testid="message-agent"]').first).to_be_visible(timeout=60000)
        page.wait_for_timeout(1000)

        # Second: explicit request to track
        page.locator('[data-testid="context-input"]').fill(
            "Actually, yes please track this as something I want to work on"
        )
        page.locator('[data-testid="send-btn"]').click()

        # Wait for second response
        expect(page.locator('[data-testid="message-agent"]').nth(1)).to_be_visible(timeout=60000)

        # Now a topic should have been created
        page.locator('[data-testid="tab-btn-topics"]').click()
        page.wait_for_timeout(1000)

        topics_container = page.locator('[data-testid="topic-list"], [data-testid="topics-container"]')
        if topics_container.is_visible():
            topic_texts = topics_container.inner_text().lower()
            assert "meditation" in topic_texts
