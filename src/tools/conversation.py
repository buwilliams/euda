"""
Conversation Control Tools.

Tools for managing the conversation state, including clearing
chat history and starting fresh conversations.
"""

# Marker that indicates a clear request was made
CLEAR_CONVERSATION_MARKER = "[[CLEAR_CONVERSATION]]"


def clear_conversation() -> str:
    """
    Clear the current conversation and start fresh.

    Returns:
        A marker string that the API will detect to signal the UI
    """
    return f"{CLEAR_CONVERSATION_MARKER}Starting fresh! How can I help you today?"


def start_new_conversation() -> str:
    """
    Start a new conversation (alias for clear_conversation).

    Returns:
        A marker string that the API will detect to signal the UI
    """
    return clear_conversation()


# Tool definitions
CONVERSATION_TOOLS = [
    {
        "name": "clear_conversation",
        "description": "Clear the chat history and start a fresh conversation. Use when the user asks to 'clear chat', 'start over', 'new conversation', 'reset chat', 'clear history', or similar.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

CONVERSATION_HANDLERS = {
    "clear_conversation": clear_conversation,
}
