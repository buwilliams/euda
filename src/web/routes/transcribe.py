"""
Transcription API Route

Handles audio file uploads and transcription using OpenAI's Audio API.
"""

import os
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

import openai


router = APIRouter()

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
                model="gpt-4o-mini-transcribe",
                file=audio_file,
                response_format="text"
            )

        return TranscriptionResponse(text=response)

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
