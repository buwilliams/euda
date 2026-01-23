"""
Transcription API Route

Handles audio file uploads and transcription using the speech provider abstraction.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from ...tools.speech import get_speech_client, supports_stt
from ...tools.speech.openai import is_openai_configured
from ...llms import get_provider


router = APIRouter()


# Maximum file size: 25MB (OpenAI limit)
MAX_FILE_SIZE = 25 * 1024 * 1024

# Supported audio formats
SUPPORTED_EXTENSIONS = {'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm'}


@router.get("/status")
def transcription_status():
    """Check if voice transcription is available for current provider."""
    provider = get_provider()

    # Check if provider supports STT
    if not supports_stt(provider):
        return {"available": False}

    # Provider-specific API key check
    if provider == "openai":
        return {"available": is_openai_configured()}

    return {"available": False}


class TranscriptionResponse(BaseModel):
    text: str


@router.post("", response_model=TranscriptionResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe audio file to text.

    Accepts audio files in mp3, mp4, mpeg, mpga, m4a, wav, or webm format.
    Maximum file size: 25MB.
    """
    provider = get_provider()

    # Check if provider supports STT
    if not supports_stt(provider):
        raise HTTPException(
            status_code=400,
            detail=f"Speech-to-text not available for provider '{provider}'"
        )

    # Get file extension
    filename = audio.filename or "audio.webm"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # Read file content
    content = await audio.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    # Check if content is empty
    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty audio file"
        )

    try:
        # Use speech client for transcription
        client = get_speech_client()
        result = client.transcribe(content, ext)
        return TranscriptionResponse(text=result.text)

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
            detail=f"Transcription error: {str(e)}"
        )
