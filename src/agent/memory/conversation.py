"""
Conversation Memory - Session-based conversation history management.

Handles:
- Session management (creating, switching sessions)
- Conversation history storage (markdown files)
- Parsing history into message objects
- Appending to long-term memory
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


class ConversationManager:
    """Manages conversation history for an agent session.

    Conversations are stored as markdown files in:
    data/agents/{agent_id}/state/conversation/{session_id}.md
    """

    def __init__(self, agent_id: str, session_id: Optional[str] = None):
        """Initialize conversation manager.

        Args:
            agent_id: The agent's ID
            session_id: Optional session ID (auto-generated if not provided)
        """
        self.agent_id = agent_id
        self._session_id = session_id

    @property
    def session_id(self) -> str:
        """Get current session ID, creating one if needed."""
        if not self._session_id:
            self._session_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        return self._session_id

    def set_session(self, session_id: str) -> None:
        """Set the current session ID.

        Args:
            session_id: New session ID
        """
        self._session_id = session_id

    def get_conversation_dir(self) -> Path:
        """Get conversation directory for this agent."""
        conv_dir = AGENTS_DIR / self.agent_id / "state" / "conversation"
        conv_dir.mkdir(parents=True, exist_ok=True)
        return conv_dir

    def get_conversation_path(self) -> Path:
        """Get path to current session's conversation file."""
        return self.get_conversation_dir() / f"{self.session_id}.md"

    def load_history(self) -> str:
        """Load current session's conversation history.

        Returns:
            Raw markdown content of conversation
        """
        path = self.get_conversation_path()
        if path.exists():
            return path.read_text()
        return ""

    def parse_history(self) -> List[dict]:
        """Parse conversation history markdown into message objects.

        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        history_text = self.load_history()
        if not history_text:
            return []

        messages = []
        # Parse markdown format: ## User (HH:MM:SS) or ## Assistant (HH:MM:SS)
        parts = re.split(r'^## (User|Assistant) \([^)]+\)\n\n', history_text, flags=re.MULTILINE)

        # parts[0] is empty or content before first header
        # parts[1] is role (User/Assistant), parts[2] is content
        # parts[3] is role, parts[4] is content, etc.
        i = 1
        while i < len(parts) - 1:
            role = parts[i].lower()
            msg_content = parts[i + 1].strip()
            if msg_content:
                messages.append({"role": role, "content": msg_content})
            i += 2

        return messages

    def save_turn(self, role: str, content: str) -> None:
        """Append a conversation turn to session file.

        Args:
            role: 'user' or 'assistant'
            content: Message content
        """
        path = self.get_conversation_path()
        timestamp = datetime.now().strftime("%H:%M:%S")

        with open(path, "a") as f:
            f.write(f"\n## {role.title()} ({timestamp})\n\n{content}\n")

    def clear_session(self) -> None:
        """Clear current session's conversation history."""
        path = self.get_conversation_path()
        if path.exists():
            path.unlink()

    def list_sessions(self) -> List[str]:
        """List all session IDs for this agent.

        Returns:
            List of session IDs (filenames without .md extension)
        """
        conv_dir = self.get_conversation_dir()
        return [f.stem for f in conv_dir.glob("*.md")]


def append_to_long_term_memory(
    user_message: str,
    assistant_response: str,
    agent_id: str,
    agent_name: str
) -> None:
    """Append a conversation exchange to today's long-term memory.

    Args:
        user_message: The user's message
        assistant_response: The assistant's response
        agent_id: The agent's ID (usually stored under 'user')
        agent_name: Display name of the agent for attribution
    """
    # Import here to avoid circular imports
    from src.core.data.memory import write_long_term_memory

    # Format the conversation for long-term memory
    content = f"**User:** {user_message}\n\n"
    content += f"**{agent_name}:** {assistant_response}"

    write_long_term_memory(content, agent_id="user", source=agent_name)
