"""
Speech Providers Package

Provides a unified interface for speech-to-text (and future text-to-speech).
"""

from .base import (
    SpeechProvider,
    TranscriptionResult,
    get_speech_client,
    supports_stt,
    supports_tts,
    invalidate_speech_client,
)

__all__ = [
    "SpeechProvider",
    "TranscriptionResult",
    "get_speech_client",
    "supports_stt",
    "supports_tts",
    "invalidate_speech_client",
]
