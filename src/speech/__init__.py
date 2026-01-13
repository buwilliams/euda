"""
Speech Providers Package

Provides a unified interface for speech-to-text and text-to-speech.
"""

from .base import (
    SpeechProvider,
    TranscriptionResult,
    SynthesisResult,
    get_speech_client,
    supports_stt,
    supports_tts,
    invalidate_speech_client,
)

__all__ = [
    "SpeechProvider",
    "TranscriptionResult",
    "SynthesisResult",
    "get_speech_client",
    "supports_stt",
    "supports_tts",
    "invalidate_speech_client",
]
