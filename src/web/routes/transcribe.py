"""
Transcription API Route

Handles audio file uploads and transcription using OpenAI's Audio API.
"""

import os
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

import openai

from ...cost_tracker import record_usage


router = APIRouter()


def is_openai_configured() -> bool:
    """Check if OpenAI API key is configured."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    # Check if key exists and isn't a placeholder
    return bool(api_key and not api_key.startswith("sk-your") and len(api_key) > 20)


@router.get("/status")
def transcription_status():
    """Check if voice transcription is available."""
    return {"available": is_openai_configured()}

# Maximum file size: 25MB (OpenAI limit)
MAX_FILE_SIZE = 25 * 1024 * 1024

# Supported audio formats
SUPPORTED_EXTENSIONS = {'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm'}


class TranscriptionResponse(BaseModel):
    text: str


@router.post("", response_model=TranscriptionResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe audio file to text using OpenAI's Audio API.

    Accepts audio files in mp3, mp4, mpeg, mpga, m4a, wav, or webm format.
    Maximum file size: 25MB.
    """
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

    # Create a temporary file for the audio
    # OpenAI SDK requires a file-like object with proper extension
    with NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Initialize OpenAI client
        client = openai.OpenAI()

        # Call OpenAI transcription API
        with open(tmp_path, 'rb') as audio_file:
            response = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio_file,
                response_format="json"
            )

        # Extract text from JSON response
        text = response.text if hasattr(response, 'text') else response.get('text', '')

        # Record cost based on audio duration or file size estimate
        # Try to get duration from response, otherwise estimate from file size (~8KB/sec)
        # Audio input is tokenized at ~50 tokens/second
        # Output tokens estimated from text length (~4 chars per token)
        duration_seconds = getattr(response, 'duration', None)
        if duration_seconds is None:
            duration_seconds = len(content) / 8000  # Fallback estimate
        estimated_input_tokens = max(1, int(duration_seconds * 50))
        estimated_output_tokens = max(1, len(text) // 4)
        record_usage(
            provider="openai",
            model="gpt-4o-transcribe",
            input_tokens=estimated_input_tokens,
            output_tokens=estimated_output_tokens,
            agent_id="transcribe"
        )

        return TranscriptionResponse(text=text.strip() if text else "")

    except openai.BadRequestError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Transcription failed: {str(e)}"
        )
    except openai.AuthenticationError:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription error: {str(e)}"
        )
    finally:
        # Clean up temp file
        os.unlink(tmp_path)
