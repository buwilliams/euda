"""
Speech Tools - Text-to-speech for agents.

Provides tools for agents to read text aloud to the user.
"""

import base64

from . import tool
from ..speech import get_speech_client, supports_tts


@tool("speak_aloud", "Read text aloud using text-to-speech. Returns audio that will be played to the user.")
def speak_aloud(text: str, voice: str = "nova") -> dict:
    """Generate speech audio from text.

    Args:
        text: The text to read aloud
        voice: Voice to use (default: 'nova')

    Returns:
        Dict with status and audio_base64, or error
    """
    if not supports_tts():
        return {"error": "Text-to-speech not available for current provider"}

    if not text or not text.strip():
        return {"error": "Empty text"}

    try:
        client = get_speech_client()
        result = client.synthesize(text=text, voice=voice)
        audio_base64 = base64.b64encode(result.audio_bytes).decode()

        return {
            "status": "generated",
            "audio_base64": audio_base64,
            "format": result.format,
            "text_length": len(text)
        }

    except Exception as e:
        return {"error": f"TTS failed: {str(e)}"}
