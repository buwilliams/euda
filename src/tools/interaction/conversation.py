"""
Conversation Control Tools.

Tools for managing the conversation state, including clearing
chat history and starting fresh conversations.
"""

# Flag to track if clear was requested during this request
_clear_requested = False


def clear_conversation() -> str:
    """
    Clear the current conversation and start fresh.

    Returns:
        Confirmation message
    """
    global _clear_requested
    _clear_requested = True
    return "Chat cleared. Starting a fresh conversation."


def start_new_conversation() -> str:
    """
    Start a new conversation (alias for clear_conversation).

    Returns:
        Confirmation message
    """
    return clear_conversation()


def was_clear_requested() -> bool:
    """Check if clear was requested and reset the flag."""
    global _clear_requested
    result = _clear_requested
    _clear_requested = False
    return result


def reset_clear_flag():
    """Reset the clear flag (call at start of each request)."""
    global _clear_requested
    _clear_requested = False


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
