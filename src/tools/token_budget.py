"""
Token Budget Manager for Ingestion Agent.

Tracks daily token usage and enforces configurable limits.
Resets automatically at the configured hour each day.
"""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional


# Data paths
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "ingestion"
CONFIG_FILE = DATA_DIR / "config.json"
BUDGET_FILE = DATA_DIR / "budget.json"

# Default config
DEFAULT_CONFIG = {
    "daily_token_limit": 1_000_000,
    "reset_hour": 0,
}

# Token estimation constants (tokens per byte, approximate)
TOKEN_ESTIMATES = {
    "text": 0.25,      # ~4 chars per token
    "image": 0.001,    # Images are processed as base64, but vision tokens are fixed
    "pdf": 0.3,        # PDFs often have more whitespace
    "audio": 0.01,     # Audio transcription is ~1 token per 4 bytes of transcript
    "video": 0.005,    # Video = keyframes + audio
    "archive": 0.1,    # Only process text contents
    "mbox": 0.25,      # Email text
    "unknown": 0.25,   # Assume text-like
}

# Fixed token costs for certain operations
VISION_TOKENS_PER_IMAGE = 1500  # Approximate for a typical image


class TokenBudget:
    """
    Manages daily token budget for ingestion processing.

    Usage:
        budget = TokenBudget()

        if budget.can_spend(estimated_tokens):
            # do processing
            budget.spend(actual_tokens)
        else:
            # defer file to tomorrow
    """

    def __init__(self):
        self.config = self._load_config()
        self.state = self._load_state()
        self._maybe_reset()

    def _load_config(self) -> dict:
        """Load configuration from file."""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                return {**DEFAULT_CONFIG, **config}
        return DEFAULT_CONFIG.copy()

    def _load_state(self) -> dict:
        """Load current budget state from file."""
        if BUDGET_FILE.exists():
            with open(BUDGET_FILE, 'r') as f:
                return json.load(f)
        return self._new_state()

    def _new_state(self) -> dict:
        """Create a fresh state for a new day."""
        return {
            "date": date.today().isoformat(),
            "used": 0,
            "transactions": []
        }

    def _save_state(self):
        """Persist state to file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(BUDGET_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)

    def _maybe_reset(self):
        """Reset budget if it's a new day."""
        state_date = self.state.get("date")
        today = date.today().isoformat()

        if state_date != today:
            # Check if we've passed the reset hour
            reset_hour = self.config.get("reset_hour", 0)
            now = datetime.now()

            if now.hour >= reset_hour or state_date != today:
                self.state = self._new_state()
                self._save_state()

    @property
    def daily_limit(self) -> int:
        """Get the configured daily token limit."""
        return self.config.get("daily_token_limit", 1_000_000)

    @property
    def used(self) -> int:
        """Get tokens used today."""
        return self.state.get("used", 0)

    @property
    def remaining(self) -> int:
        """Get tokens remaining today."""
        return max(0, self.daily_limit - self.used)

    def can_spend(self, tokens: int) -> bool:
        """Check if we can spend the given number of tokens."""
        self._maybe_reset()
        return self.used + tokens <= self.daily_limit

    def spend(self, tokens: int, description: str = ""):
        """
        Record token usage.

        Args:
            tokens: Number of tokens used
            description: Optional description of what was processed
        """
        self._maybe_reset()
        self.state["used"] = self.state.get("used", 0) + tokens

        # Keep a transaction log (last 100 entries)
        transactions = self.state.get("transactions", [])
        transactions.append({
            "time": datetime.now().isoformat(),
            "tokens": tokens,
            "description": description[:100] if description else ""
        })
        self.state["transactions"] = transactions[-100:]

        self._save_state()

    def estimate_tokens(self, file_size: int, file_type: str) -> int:
        """
        Estimate tokens needed to process a file.

        Args:
            file_size: Size of file in bytes
            file_type: Type category (image, pdf, text, etc.)

        Returns:
            Estimated token count
        """
        # Get the multiplier for this file type
        multiplier = TOKEN_ESTIMATES.get(file_type, TOKEN_ESTIMATES["unknown"])

        # Calculate base estimate
        estimated = int(file_size * multiplier)

        # Add fixed costs for certain types
        if file_type == "image":
            estimated = max(estimated, VISION_TOKENS_PER_IMAGE)

        # Minimum of 100 tokens (overhead)
        return max(100, estimated)

    def get_status(self) -> dict:
        """Get current budget status."""
        self._maybe_reset()
        return {
            "daily_limit": self.daily_limit,
            "used": self.used,
            "remaining": self.remaining,
            "percent_used": round(self.used / self.daily_limit * 100, 1) if self.daily_limit > 0 else 0,
            "date": self.state.get("date"),
            "reset_hour": self.config.get("reset_hour", 0),
            "transaction_count": len(self.state.get("transactions", []))
        }

    def reload_config(self):
        """Reload configuration from file."""
        self.config = self._load_config()


# Singleton instance for easy access
_budget_instance: Optional[TokenBudget] = None


def get_budget() -> TokenBudget:
    """Get the singleton TokenBudget instance."""
    global _budget_instance
    if _budget_instance is None:
        _budget_instance = TokenBudget()
    return _budget_instance


# Tool functions for agent use
def check_token_budget() -> str:
    """Check the current token budget status."""
    budget = get_budget()
    status = budget.get_status()
    return (
        f"Token Budget Status:\n"
        f"  Daily limit: {status['daily_limit']:,} tokens\n"
        f"  Used today: {status['used']:,} tokens ({status['percent_used']}%)\n"
        f"  Remaining: {status['remaining']:,} tokens\n"
        f"  Resets at: {status['reset_hour']:02d}:00"
    )


def can_afford_tokens(tokens: int) -> str:
    """Check if we can afford to spend the given number of tokens."""
    budget = get_budget()
    if budget.can_spend(tokens):
        return f"Yes, can afford {tokens:,} tokens. Remaining: {budget.remaining:,}"
    else:
        return f"No, cannot afford {tokens:,} tokens. Only {budget.remaining:,} remaining."


def record_token_usage(tokens: int, description: str = "") -> str:
    """Record token usage after processing a file."""
    budget = get_budget()
    budget.spend(tokens, description)
    return f"Recorded {tokens:,} tokens. Remaining today: {budget.remaining:,}"


# Tool definitions for LLM
TOKEN_BUDGET_TOOLS = [
    {
        "name": "check_token_budget",
        "description": "Check the current daily token budget status - how much has been used and how much remains.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "can_afford_tokens",
        "description": "Check if we can afford to spend a given number of tokens without exceeding the daily limit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tokens": {
                    "type": "integer",
                    "description": "Number of tokens to check"
                }
            },
            "required": ["tokens"]
        }
    },
    {
        "name": "record_token_usage",
        "description": "Record token usage after processing a file. Call this after successful AI processing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tokens": {
                    "type": "integer",
                    "description": "Number of tokens used"
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what was processed"
                }
            },
            "required": ["tokens"]
        }
    }
]

TOKEN_BUDGET_HANDLERS = {
    "check_token_budget": lambda: check_token_budget(),
    "can_afford_tokens": can_afford_tokens,
    "record_token_usage": record_token_usage,
}


# Test
if __name__ == "__main__":
    budget = TokenBudget()
    print(check_token_budget())
    print()
    print(f"Can afford 1000? {budget.can_spend(1000)}")
    print(f"Estimate for 10KB text: {budget.estimate_tokens(10000, 'text')} tokens")
    print(f"Estimate for 1MB image: {budget.estimate_tokens(1000000, 'image')} tokens")
