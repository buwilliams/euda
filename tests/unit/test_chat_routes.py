"""
Unit tests for chat routes module.

Tests for src/web/routes/chat.py - conversation management functionality.
"""

import json
import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestChatRequestResponse:
    """Test chat request/response models use conversation_id."""

    def test_chat_request_has_conversation_id(self):
        """ChatRequest should have conversation_id field."""
        from src.web.routes.chat import ChatRequest

        request = ChatRequest(message="test", conversation_id="conv-123")
        assert request.conversation_id == "conv-123"

    def test_chat_request_conversation_id_optional(self):
        """ChatRequest conversation_id should be optional."""
        from src.web.routes.chat import ChatRequest

        request = ChatRequest(message="test")
        assert request.conversation_id is None

    def test_chat_response_has_conversation_id(self):
        """ChatResponse should have conversation_id field."""
        from src.web.routes.chat import ChatResponse

        response = ChatResponse(
            response="Hello",
            agent_id="user",
            conversation_id="conv-456"
        )
        assert response.conversation_id == "conv-456"


class TestForkRequest:
    """Test ForkRequest model uses conversation_id."""

    def test_fork_request_has_conversation_id(self):
        """ForkRequest should have conversation_id field."""
        from src.web.routes.chat import ForkRequest

        request = ForkRequest(conversation_id="conv-789")
        assert request.conversation_id == "conv-789"


class TestRecentConversations:
    """Test recent conversations endpoint."""

    @pytest.fixture
    def temp_conv_dir(self, tmp_path):
        """Create a temporary conversation directory."""
        conv_dir = tmp_path / "data" / "agents" / "user" / "state" / "conversation"
        conv_dir.mkdir(parents=True)
        return conv_dir

    @pytest.fixture
    def patch_conv_dir(self, temp_conv_dir):
        """Patch CONV_DIR to use temp directory."""
        with patch('src.web.routes.chat.CONV_DIR', temp_conv_dir):
            yield temp_conv_dir

    def test_recent_conversations_returns_conversation_id(self, patch_conv_dir):
        """Recent conversations should return conversation_id, not session_id."""
        from src.web.routes.chat import get_recent_conversations

        # Create a test conversation file
        conv_file = patch_conv_dir / "test-conv-123.md"
        conv_file.write_text("## User (12:00:00)\n\nHello world\n\n## Assistant (12:00:05)\n\nHi there!")

        result = get_recent_conversations(count=5)

        assert "conversations" in result
        assert len(result["conversations"]) == 1
        assert "conversation_id" in result["conversations"][0]
        assert result["conversations"][0]["conversation_id"] == "test-conv-123"
        # Ensure session_id is NOT present
        assert "session_id" not in result["conversations"][0]

    def test_recent_conversations_includes_last_message_timestamp(self, patch_conv_dir):
        """Most recent conversation should include last_message_timestamp."""
        from src.web.routes.chat import get_recent_conversations

        # Create a test conversation file
        conv_file = patch_conv_dir / "conv-with-timestamp.md"
        conv_file.write_text("## User (12:00:00)\n\nTest message")

        result = get_recent_conversations(count=5)

        assert len(result["conversations"]) == 1
        conv = result["conversations"][0]
        assert "last_message_timestamp" in conv
        assert isinstance(conv["last_message_timestamp"], int)
        # Timestamp should be recent (within last hour)
        now = int(time.time())
        assert now - conv["last_message_timestamp"] < 3600

    def test_only_most_recent_has_timestamp(self, patch_conv_dir):
        """Only the most recent conversation should have last_message_timestamp."""
        from src.web.routes.chat import get_recent_conversations
        import time

        # Create multiple conversation files with different mtimes
        conv1 = patch_conv_dir / "conv-older.md"
        conv1.write_text("## User (10:00:00)\n\nOlder message")

        # Sleep to ensure different mtime
        time.sleep(0.1)

        conv2 = patch_conv_dir / "conv-newer.md"
        conv2.write_text("## User (11:00:00)\n\nNewer message")

        result = get_recent_conversations(count=5)

        assert len(result["conversations"]) == 2

        # Most recent (first in list) should have timestamp
        assert "last_message_timestamp" in result["conversations"][0]

        # Older conversations should NOT have timestamp
        assert "last_message_timestamp" not in result["conversations"][1]

    def test_empty_conversations_returns_empty_list(self, patch_conv_dir):
        """Empty conversation directory should return empty list."""
        from src.web.routes.chat import get_recent_conversations

        result = get_recent_conversations(count=5)

        assert result == {"conversations": []}


class TestForkConversation:
    """Test fork conversation endpoint."""

    @pytest.fixture
    def temp_conv_dir(self, tmp_path):
        """Create a temporary conversation directory."""
        conv_dir = tmp_path / "data" / "agents" / "user" / "state" / "conversation"
        conv_dir.mkdir(parents=True)
        return conv_dir

    @pytest.fixture
    def patch_conv_dir(self, temp_conv_dir):
        """Patch CONV_DIR to use temp directory."""
        with patch('src.web.routes.chat.CONV_DIR', temp_conv_dir):
            yield temp_conv_dir

    def test_fork_returns_new_conversation_id(self, patch_conv_dir):
        """Fork should return new_conversation_id, not new_session_id."""
        from src.web.routes.chat import fork_conversation, ForkRequest

        # Create a test conversation
        conv_file = patch_conv_dir / "fork-test.md"
        conv_file.write_text("## User (12:00:00)\n\nHello\n\n## Assistant (12:00:05)\n\nHi!")

        request = ForkRequest(conversation_id="fork-test")
        result = fork_conversation(request)

        assert "new_conversation_id" in result
        assert result["new_conversation_id"] == "fork-test"
        # Ensure new_session_id is NOT present
        assert "new_session_id" not in result

    def test_fork_returns_messages(self, patch_conv_dir):
        """Fork should return parsed messages."""
        from src.web.routes.chat import fork_conversation, ForkRequest

        conv_file = patch_conv_dir / "msg-test.md"
        conv_file.write_text("## User (12:00:00)\n\nUser message here\n\n## Assistant (12:00:05)\n\nAssistant response")

        request = ForkRequest(conversation_id="msg-test")
        result = fork_conversation(request)

        assert "messages" in result
        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"] == "User message here"
        assert result["messages"][1]["role"] == "assistant"
        assert result["messages"][1]["content"] == "Assistant response"


class TestDeleteConversation:
    """Test delete conversation endpoint."""

    @pytest.fixture
    def temp_conv_dir(self, tmp_path):
        """Create a temporary conversation directory."""
        conv_dir = tmp_path / "data" / "agents" / "user" / "state" / "conversation"
        conv_dir.mkdir(parents=True)
        return conv_dir

    @pytest.fixture
    def patch_conv_dir(self, temp_conv_dir):
        """Patch CONV_DIR to use temp directory."""
        with patch('src.web.routes.chat.CONV_DIR', temp_conv_dir):
            yield temp_conv_dir

    def test_delete_returns_conversation_id(self, patch_conv_dir):
        """Delete should return conversation_id, not session_id."""
        from src.web.routes.chat import delete_conversation

        # Create a test conversation
        conv_file = patch_conv_dir / "delete-test.md"
        conv_file.write_text("## User (12:00:00)\n\nTo be deleted")

        result = delete_conversation("delete-test")

        assert result["status"] == "deleted"
        assert "conversation_id" in result
        assert result["conversation_id"] == "delete-test"
        # Ensure session_id is NOT present
        assert "session_id" not in result

    def test_delete_removes_file(self, patch_conv_dir):
        """Delete should remove the conversation file."""
        from src.web.routes.chat import delete_conversation

        conv_file = patch_conv_dir / "to-remove.md"
        conv_file.write_text("## User (12:00:00)\n\nGoodbye")

        assert conv_file.exists()
        delete_conversation("to-remove")
        assert not conv_file.exists()

    def test_delete_nonexistent_raises_404(self, patch_conv_dir):
        """Delete nonexistent conversation should raise 404."""
        from src.web.routes.chat import delete_conversation
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            delete_conversation("nonexistent-conv")

        assert exc_info.value.status_code == 404


class TestConversationThreshold:
    """Test 6-hour conversation resume threshold logic."""

    def test_timestamp_is_unix_seconds(self, tmp_path):
        """Timestamp should be unix seconds, not milliseconds."""
        from src.web.routes.chat import get_recent_conversations

        conv_dir = tmp_path / "data" / "agents" / "user" / "state" / "conversation"
        conv_dir.mkdir(parents=True)

        conv_file = conv_dir / "time-test.md"
        conv_file.write_text("## User (12:00:00)\n\nTest")

        with patch('src.web.routes.chat.CONV_DIR', conv_dir):
            result = get_recent_conversations(count=1)

        timestamp = result["conversations"][0]["last_message_timestamp"]

        # Unix seconds are ~10 digits, milliseconds are ~13 digits
        assert len(str(timestamp)) == 10, "Timestamp should be in seconds, not milliseconds"

        # Should be a reasonable unix timestamp (after year 2020)
        assert timestamp > 1577836800, "Timestamp should be after Jan 1, 2020"
