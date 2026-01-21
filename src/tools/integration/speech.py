"""
Speech Tools - Text-to-speech for agents.

Provides tools for agents to read text aloud to the user.
"""

import base64

from .. import tool
from ...speech import get_speech_client, supports_tts
from ...web.events import emit_ui_event


@tool("speak_aloud", "Read text aloud using text-to-speech. The audio will be played through the user's speakers.", tool_type="integration")
def speak_aloud(text: str, voice: str = "nova") -> dict:
    """Generate speech audio from text and play it to the user.

    Args:
        text: The text to read aloud
        voice: Voice to use (default: 'nova')

    Returns:
        Dict with status, or error
    """
    if not supports_tts():
        return {"error": "Text-to-speech not available for current provider"}

    if not text or not text.strip():
        return {"error": "Empty text"}

    try:
        client = get_speech_client()
        result = client.synthesize(text=text, voice=voice)
        audio_base64 = base64.b64encode(result.audio_bytes).decode()

        # Emit SSE event to play audio on frontend
        emit_ui_event("tts_audio", {"audio_base64": audio_base64})

        return {
            "status": "playing",
            "text_length": len(text)
        }

    except Exception as e:
        return {"error": f"TTS failed: {str(e)}"}
