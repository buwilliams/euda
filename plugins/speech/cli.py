"""Speech plugin for Euno - Text-to-speech capabilities."""

import sys
from pathlib import Path
from typing import Optional

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

app = typer.Typer(
    name="speech",
    help="Text-to-speech operations.",
    no_args_is_help=True,
)


@app.command("speak")
def speak_cmd(
    text: str = typer.Argument(..., help="Text to speak"),
    voice: str = typer.Option("nova", "--voice", "-v", help="Voice to use (default: nova)"),
):
    """Read text aloud using text-to-speech.

    The audio will be played through the user's speakers if connected.
    """
    from plugins.speech.integration import speak_aloud

    result = speak_aloud(text=text, voice=voice)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Text length: {result.get('text_length', 0)} characters")


@app.command("voices")
def voices_cmd():
    """List available TTS voices."""
    # OpenAI TTS voices
    voices = [
        ("alloy", "Neutral, balanced"),
        ("echo", "Male, warm"),
        ("fable", "British accent"),
        ("onyx", "Male, deep"),
        ("nova", "Female, friendly (default)"),
        ("shimmer", "Female, soft"),
    ]

    print("Available voices:")
    for voice_id, description in voices:
        default = " (default)" if voice_id == "nova" else ""
        print(f"  {voice_id}: {description}{default}")


def main():
    """Entry point for the speech plugin CLI."""
    app()


if __name__ == "__main__":
    main()
