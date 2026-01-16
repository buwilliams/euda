"""
Speech Base Classes and Configuration

Provides abstract base class for speech providers and unified client.
Follows the same pattern as src/llms/base.py.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..llms import get_provider


# Provider capabilities for speech features
# STT = Speech-to-Text, TTS = Text-to-Speech
PROVIDER_CAPABILITIES = {
    "openai": {"stt": True, "tts": True},
    "anthropic": {"stt": False, "tts": False},
    "grok": {"stt": False, "tts": False},
}


# ============== Response Classes ==============

@dataclass
class TranscriptionResult:
    """Result from speech-to-text transcription."""
    text: str
    duration_seconds: Optional[float] = None
    language: Optional[str] = None


@dataclass
class SynthesisResult:
    """Result from text-to-speech synthesis."""
    audio_bytes: bytes
    format: str  # 'mp3', 'wav', etc.
    duration_seconds: Optional[float] = None


# ============== Abstract Provider ==============

class SpeechProvider(ABC):
    """Abstract base class for speech providers."""

    @abstractmethod
    def transcribe(
        self,
        audio_bytes: bytes,
        audio_format: str,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe audio to text.

        Args:
            audio_bytes: Raw audio data
            audio_format: Audio format (e.g., 'webm', 'mp3', 'wav')
            language: Optional language hint (ISO 639-1 code)

        Returns:
            TranscriptionResult with transcribed text
        """
        pass

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: str = "nova",
        instructions: Optional[str] = None
    ) -> SynthesisResult:
        """Synthesize text to speech audio.

        Args:
            text: Text to synthesize
            voice: Voice to use (default: 'nova')
            instructions: Optional instructions for speech style

        Returns:
            SynthesisResult with audio bytes
        """
        pass

    @classmethod
    def supports_stt(cls) -> bool:
        """Whether this provider supports speech-to-text."""
        return True

    @classmethod
    def supports_tts(cls) -> bool:
        """Whether this provider supports text-to-speech."""
        return False


# ============== Capability Helpers ==============

def supports_stt(provider_id: Optional[str] = None) -> bool:
    """Check if a provider supports speech-to-text.

    Args:
        provider_id: Provider to check. If None, uses current LLM provider.

    Returns:
        True if provider supports STT
    """
    if provider_id is None:
        provider_id = get_provider()
    return PROVIDER_CAPABILITIES.get(provider_id, {}).get("stt", False)


def supports_tts(provider_id: Optional[str] = None) -> bool:
    """Check if a provider supports text-to-speech.

    Args:
        provider_id: Provider to check. If None, uses current LLM provider.

    Returns:
        True if provider supports TTS
    """
    if provider_id is None:
        provider_id = get_provider()
    return PROVIDER_CAPABILITIES.get(provider_id, {}).get("tts", False)


# ============== Provider Factory ==============

# Cached client instance
_cached_speech_client: "UnifiedSpeechClient" = None


def get_speech_client() -> "UnifiedSpeechClient":
    """Get a unified speech client for the current LLM provider.

    Returns cached client, creating one if cache was invalidated.
    """
    global _cached_speech_client

    if _cached_speech_client is None:
        provider = get_provider()
        _cached_speech_client = UnifiedSpeechClient(provider)

    return _cached_speech_client


def invalidate_speech_client():
    """Invalidate cached speech client. Call when settings change."""
    global _cached_speech_client
    _cached_speech_client = None


class UnifiedSpeechClient:
    """Wrapper that delegates to the appropriate speech provider.

    Handles cross-cutting concerns:
    - Cost tracking (after each call)
    - Rate limiting with exponential backoff
    """

    def __init__(self, provider: str):
        self.provider_name = provider
        self._provider = self._create_provider(provider)

        # Rate limiting state
        self._backoff_until: Optional[float] = None
        self._consecutive_rate_limits: int = 0

    def _create_provider(self, provider: str) -> Optional[SpeechProvider]:
        """Create the appropriate speech provider instance."""
        if provider == "openai":
            from .openai import OpenAISpeechProvider
            return OpenAISpeechProvider()
        else:
            # Provider doesn't support speech - return None
            return None

    def _wait_for_backoff(self):
        """Block until backoff period ends."""
        if self._backoff_until and time.time() < self._backoff_until:
            wait_time = self._backoff_until - time.time()
            print(f"[Speech] Rate limited, waiting {wait_time:.1f}s...")
            time.sleep(wait_time)

    def _handle_rate_limit(self):
        """Calculate and set backoff after a rate limit."""
        self._consecutive_rate_limits += 1
        # Exponential backoff: 2, 4, 8, 16... up to 240 seconds
        backoff_seconds = min(2 ** self._consecutive_rate_limits, 240)
        self._backoff_until = time.time() + backoff_seconds
        print(f"[Speech] Rate limit hit, backing off {backoff_seconds}s")

    def _reset_backoff(self):
        """Reset backoff state after successful call."""
        self._consecutive_rate_limits = 0
        self._backoff_until = None

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an exception is a rate limit error."""
        error_str = str(error).lower()
        return any(phrase in error_str for phrase in [
            "429", "rate_limit", "rate limit", "too many requests"
        ])

    def transcribe(
        self,
        audio_bytes: bytes,
        audio_format: str,
        language: Optional[str] = None,
        track_cost: bool = True
    ) -> TranscriptionResult:
        """Transcribe audio to text with automatic cost tracking.

        Args:
            audio_bytes: Raw audio data
            audio_format: Audio format (e.g., 'webm', 'mp3', 'wav')
            language: Optional language hint
            track_cost: Whether to track costs (default True)

        Returns:
            TranscriptionResult with transcribed text

        Raises:
            ValueError: If provider doesn't support speech-to-text
        """
        if self._provider is None:
            raise ValueError(f"Provider '{self.provider_name}' does not support speech-to-text")

        from ..metacognition import record_usage

        # Wait for any active backoff
        self._wait_for_backoff()

        # Make the transcription call
        start_time = time.time()
        try:
            result = self._provider.transcribe(audio_bytes, audio_format, language)
        except Exception as e:
            if self._is_rate_limit_error(e):
                self._handle_rate_limit()
            raise

        duration_ms = int((time.time() - start_time) * 1000)

        # Reset backoff on success
        self._reset_backoff()

        # Record usage/cost
        if track_cost:
            # Estimate tokens based on audio duration
            # Audio is tokenized at ~50 tokens/second
            audio_duration = result.duration_seconds
            if audio_duration is None:
                # Fallback: estimate from file size (~8KB/sec for typical audio)
                audio_duration = len(audio_bytes) / 8000

            estimated_input_tokens = max(1, int(audio_duration * 50))
            estimated_output_tokens = max(1, len(result.text) // 4)

            record_usage(
                provider=self.provider_name,
                model="gpt-4o-transcribe",
                input_tokens=estimated_input_tokens,
                output_tokens=estimated_output_tokens,
                agent_id="transcribe",
                duration_ms=duration_ms
            )

        return result

    def synthesize(
        self,
        text: str,
        voice: str = "nova",
        instructions: Optional[str] = None,
        track_cost: bool = True
    ) -> SynthesisResult:
        """Synthesize text to speech with automatic cost tracking.

        Args:
            text: Text to synthesize
            voice: Voice to use (default: 'nova')
            instructions: Optional instructions for speech style
            track_cost: Whether to track costs (default True)

        Returns:
            SynthesisResult with audio bytes

        Raises:
            ValueError: If provider doesn't support text-to-speech
        """
        if self._provider is None:
            raise ValueError(f"Provider '{self.provider_name}' does not support text-to-speech")

        from ..metacognition import record_usage

        # Wait for any active backoff
        self._wait_for_backoff()

        # Make the synthesis call
        start_time = time.time()
        try:
            result = self._provider.synthesize(text, voice, instructions)
        except Exception as e:
            if self._is_rate_limit_error(e):
                self._handle_rate_limit()
            raise

        duration_ms = int((time.time() - start_time) * 1000)

        # Reset backoff on success
        self._reset_backoff()

        # Record usage/cost
        if track_cost:
            # Estimate tokens: ~15 characters per token for TTS
            estimated_input_tokens = max(1, len(text) // 15)

            record_usage(
                provider=self.provider_name,
                model="gpt-4o-mini-tts",
                input_tokens=estimated_input_tokens,
                output_tokens=0,
                agent_id="tts",
                duration_ms=duration_ms
            )

        return result
