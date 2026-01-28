"""
Synthesis API Route

Handles text-to-speech synthesis using the speech provider abstraction.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from src.speech import get_speech_client, supports_tts
from src.speech.openai import is_openai_configured
from ...llms import get_provider


router = APIRouter()


@router.get("/status")
def synthesis_status():
    """Check if text-to-speech is available for current provider."""
    provider = get_provider()

    # Check if provider supports TTS
    if not supports_tts(provider):
        return {"available": False}

    # Provider-specific API key check
    if provider == "openai":
        return {"available": is_openai_configured()}

    return {"available": False}


class SynthesisRequest(BaseModel):
    text: str
    voice: str = "nova"
    instructions: Optional[str] = None


@router.post("")
def synthesize_text(request: SynthesisRequest):
    """Synthesize text to speech audio.

    Returns audio/mpeg binary stream.
    """
    provider = get_provider()

    # Check if provider supports TTS
    if not supports_tts(provider):
        raise HTTPException(
            status_code=400,
            detail=f"Text-to-speech not available for provider '{provider}'"
        )

    # Check if text is empty
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Empty text"
        )

    try:
        # Use speech client for synthesis
        client = get_speech_client()
        result = client.synthesize(
            text=request.text,
            voice=request.voice,
            instructions=request.instructions
        )

        # Return audio as binary stream
        return Response(
            content=result.audio_bytes,
            media_type="audio/mpeg"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        error_str = str(e).lower()
        if "authentication" in error_str or "api key" in error_str:
            raise HTTPException(
                status_code=500,
                detail="API key not configured for speech provider"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Synthesis error: {str(e)}"
        )
