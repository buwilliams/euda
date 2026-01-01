"""
Conversation Control Tools.

Tools for managing the conversation state, including clearing
chat history and starting fresh conversations.
"""

# Flags to track if clear/delete was requested during this request
_clear_requested = False
_delete_requested = False


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


def delete_current_conversation() -> str:
    """
    Delete the current conversation permanently from history.

    Returns:
        Confirmation message
    """
    global _delete_requested
    _delete_requested = True
    return "This conversation will be permanently deleted."


def was_delete_requested() -> bool:
    """Check if delete was requested."""
    return _delete_requested


def reset_delete_flag():
    """Reset the delete flag (call at start of each request)."""
    global _delete_requested
    _delete_requested = False


# Tool definitions
CONVERSATION_TOOLS = [
    {
        "name": "clear_conversation",
        "description": "Clear the chat history and start a fresh conversation. Use when the user asks to 'clear chat', 'start over', 'new conversation', 'reset chat', 'clear history', or similar.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "delete_current_conversation",
        "description": "PERMANENTLY delete the current conversation from history. This cannot be undone. IMPORTANT: Before calling this tool, you MUST first confirm with the user by asking 'Are you sure you want to permanently delete this conversation?' Only call this tool after the user confirms.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

CONVERSATION_HANDLERS = {
    "clear_conversation": clear_conversation,
    "delete_current_conversation": delete_current_conversation,
}
