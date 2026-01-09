"""
OpenAI Speech Provider

Implements speech-to-text using OpenAI's Audio API.
"""

import os
from tempfile import NamedTemporaryFile
from typing import Optional

import openai

from .base import SpeechProvider, TranscriptionResult


def is_openai_configured() -> bool:
    """Check if OpenAI API key is configured."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    # Check if key exists and isn't a placeholder
    return bool(api_key and not api_key.startswith("sk-your") and len(api_key) > 20)


class OpenAISpeechProvider(SpeechProvider):
    """OpenAI speech provider using Whisper/GPT-4o transcription."""

    # Supported audio formats
    SUPPORTED_FORMATS = {'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm'}

    # Maximum file size: 25MB (OpenAI limit)
    MAX_FILE_SIZE = 25 * 1024 * 1024

    def __init__(self):
        self._client = openai.OpenAI()

    @classmethod
    def supports_stt(cls) -> bool:
        return True

    @classmethod
    def supports_tts(cls) -> bool:
        return True  # OpenAI has TTS API too

    def transcribe(
        self,
        audio_bytes: bytes,
        audio_format: str,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe audio using OpenAI's transcription API.

        Args:
            audio_bytes: Raw audio data
            audio_format: Audio format extension (e.g., 'webm', 'mp3')
            language: Optional ISO 639-1 language code

        Returns:
            TranscriptionResult with transcribed text

        Raises:
            ValueError: If format not supported or file too large
            openai.BadRequestError: If transcription fails
        """
        # Normalize format
        fmt = audio_format.lower().lstrip('.')

        if fmt not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported audio format '{fmt}'. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        if len(audio_bytes) > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File too large. Maximum size: {self.MAX_FILE_SIZE // (1024*1024)}MB"
            )

        if len(audio_bytes) == 0:
            raise ValueError("Empty audio file")

        # Create temp file (OpenAI SDK requires file-like object with extension)
        with NamedTemporaryFile(suffix=f".{fmt}", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            # Call OpenAI transcription API
            with open(tmp_path, 'rb') as audio_file:
                response = self._client.audio.transcriptions.create(
                    model="gpt-4o-transcribe",
                    file=audio_file,
                    response_format="json"
                )

            # Extract result
            text = response.text if hasattr(response, 'text') else ""
            duration = getattr(response, 'duration', None)

            return TranscriptionResult(
                text=text.strip() if text else "",
                duration_seconds=duration,
                language=language
            )

        finally:
            # Clean up temp file
            os.unlink(tmp_path)
