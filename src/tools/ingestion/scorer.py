"""
Relevance Scorer for Ingestion Agent.

Scores files 0.0-1.0 based on:
- Recency (newer files score higher)
- Type weight (photos > documents > logs)
- Size penalty (very large files score lower)
- Source bonus (emails, exports score higher)

Higher scores = process first.
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# Data paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "ingestion"
CONFIG_FILE = DATA_DIR / "config.json"

# Default type weights (can be overridden in config)
DEFAULT_TYPE_WEIGHTS = {
    "image": 1.0,      # Photos are high-value personal data
    "pdf": 0.9,        # Documents often important
    "mbox": 0.9,       # Email exports very valuable
    "audio": 0.8,      # Voice memos, podcasts
    "video": 0.8,      # Personal videos
    "text": 0.7,       # Notes, logs
    "archive": 0.5,    # Need extraction, lower priority
    "unknown": 0.3,    # Uncertain value
}

# Size thresholds for penalty calculation
SIZE_THRESHOLDS = {
    "ideal": 100_000,       # 100KB - ideal size, no penalty
    "large": 10_000_000,    # 10MB - start penalizing
    "huge": 100_000_000,    # 100MB - significant penalty
}

# Recency decay half-life in days
RECENCY_HALF_LIFE_DAYS = 30


def _load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def score_recency(timestamp: Optional[str], reference: Optional[datetime] = None) -> float:
    """
    Score based on how recent the file is.

    Uses exponential decay with configurable half-life.
    Returns 1.0 for "now", decaying towards 0 for older files.

    Args:
        timestamp: ISO format timestamp string
        reference: Reference time (defaults to now)

    Returns:
        Score between 0.0 and 1.0
    """
    if not timestamp:
        return 0.3  # Unknown date gets low score

    if reference is None:
        reference = datetime.now()

    try:
        # Parse the timestamp
        if 'T' in timestamp:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(timestamp)

        # Make naive if needed for comparison
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)

        # Calculate age in days
        age_days = (reference - dt).days

        if age_days < 0:
            # Future date (probably an error) - treat as recent
            return 0.9

        if age_days == 0:
            return 1.0

        # Exponential decay
        # score = 0.5^(age/half_life)
        decay = math.pow(0.5, age_days / RECENCY_HALF_LIFE_DAYS)

        # Don't go below 0.1 for any valid date
        return max(0.1, decay)

    except (ValueError, TypeError):
        return 0.3  # Parse error - unknown date


def score_type(category: str) -> float:
    """
    Score based on file type/category.

    Args:
        category: File category (image, pdf, text, etc.)

    Returns:
        Score between 0.0 and 1.0
    """
    config = _load_config()
    weights = config.get("type_weights", DEFAULT_TYPE_WEIGHTS)
    return weights.get(category, DEFAULT_TYPE_WEIGHTS.get("unknown", 0.3))


def score_size(size_bytes: int) -> float:
    """
    Score based on file size.

    Small to medium files get full score.
    Large files get penalized (expensive to process).

    Args:
        size_bytes: File size in bytes

    Returns:
        Score between 0.0 and 1.0
    """
    if size_bytes <= SIZE_THRESHOLDS["ideal"]:
        return 1.0

    if size_bytes <= SIZE_THRESHOLDS["large"]:
        # Linear decay from 1.0 to 0.8
        ratio = (size_bytes - SIZE_THRESHOLDS["ideal"]) / (SIZE_THRESHOLDS["large"] - SIZE_THRESHOLDS["ideal"])
        return 1.0 - (0.2 * ratio)

    if size_bytes <= SIZE_THRESHOLDS["huge"]:
        # Linear decay from 0.8 to 0.4
        ratio = (size_bytes - SIZE_THRESHOLDS["large"]) / (SIZE_THRESHOLDS["huge"] - SIZE_THRESHOLDS["large"])
        return 0.8 - (0.4 * ratio)

    # Huge files get low score
    return 0.4


def score_source(file_path: str, digest: dict) -> float:
    """
    Score based on apparent source of the file.

    Certain sources indicate higher-value content:
    - Email exports
    - Chat exports
    - Personal photos (camera roll patterns)

    Args:
        file_path: Path to the file
        digest: File digest with metadata

    Returns:
        Bonus score to add (0.0 to 0.2)
    """
    name = Path(file_path).name.lower()
    path_str = str(file_path).lower()

    bonus = 0.0

    # Email/chat exports
    if any(x in name for x in ['export', 'backup', 'archive']):
        bonus += 0.1
    if any(x in path_str for x in ['email', 'mail', 'messages', 'chat']):
        bonus += 0.1

    # Camera patterns (personal photos)
    if any(x in name for x in ['img_', 'dsc', 'photo', 'camera']):
        bonus += 0.05

    # Screenshots (often useful reference)
    if 'screenshot' in name:
        bonus += 0.05

    # Check for high-confidence temporal data (indicates organized content)
    temporal = digest.get("temporal_hints", {})
    if temporal.get("confidence") == "high":
        bonus += 0.05

    return min(0.2, bonus)


def calculate_score(digest: dict) -> float:
    """
    Calculate overall relevance score for a file.

    Combines multiple factors:
    - Recency (40% weight)
    - Type (30% weight)
    - Size (20% weight)
    - Source bonus (10% max)

    Args:
        digest: Complete file digest

    Returns:
        Score between 0.0 and 1.0
    """
    classification = digest.get("classification", {})
    file_path = classification.get("path", "")

    # Get component scores
    temporal = digest.get("temporal_hints", {})
    recency = score_recency(temporal.get("timestamp"))

    category = classification.get("category", "unknown")
    type_score = score_type(category)

    size = classification.get("size", 0)
    size_score = score_size(size)

    source_bonus = score_source(file_path, digest)

    # Weighted combination
    # Recency: 40%, Type: 30%, Size: 20%, Source: 10% bonus
    base_score = (
        recency * 0.4 +
        type_score * 0.3 +
        size_score * 0.2
    )

    # Add source bonus (capped at 0.1 of final score)
    final_score = min(1.0, base_score + source_bonus * 0.5)

    return round(final_score, 3)


def score_file(file_path: str, digest: Optional[dict] = None) -> dict:
    """
    Score a file and return detailed breakdown.

    Args:
        file_path: Path to the file
        digest: Optional pre-generated digest

    Returns:
        Dict with score and breakdown
    """
    if digest is None:
        from .digest import generate_digest
        digest = generate_digest(file_path)

    classification = digest.get("classification", {})
    temporal = digest.get("temporal_hints", {})

    recency = score_recency(temporal.get("timestamp"))
    type_score = score_type(classification.get("category", "unknown"))
    size_score = score_size(classification.get("size", 0))
    source_bonus = score_source(file_path, digest)
    final = calculate_score(digest)

    return {
        "file": classification.get("name", Path(file_path).name),
        "score": final,
        "breakdown": {
            "recency": recency,
            "type": type_score,
            "size": size_score,
            "source_bonus": source_bonus,
        },
        "factors": {
            "category": classification.get("category", "unknown"),
            "size_bytes": classification.get("size", 0),
            "timestamp": temporal.get("timestamp"),
            "temporal_confidence": temporal.get("confidence", "unknown"),
        }
    }


# Tool definitions for LLM
SCORER_TOOLS = [
    {
        "name": "score_file_relevance",
        "description": "Calculate the relevance score for a file. Higher scores (0.0-1.0) indicate higher priority for processing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to score"
                }
            },
            "required": ["file_path"]
        }
    }
]


def _score_file_tool(file_path: str) -> str:
    """Tool wrapper for score_file."""
    result = score_file(file_path)
    return json.dumps(result, indent=2)


SCORER_HANDLERS = {
    "score_file_relevance": _score_file_tool,
}


# Test
if __name__ == "__main__":
    # Test recency scoring
    print("=== Recency Scoring ===")
    now = datetime.now()
    test_dates = [
        ("Today", now.isoformat()),
        ("Yesterday", (now - timedelta(days=1)).isoformat()),
        ("1 week ago", (now - timedelta(days=7)).isoformat()),
        ("1 month ago", (now - timedelta(days=30)).isoformat()),
        ("3 months ago", (now - timedelta(days=90)).isoformat()),
        ("1 year ago", (now - timedelta(days=365)).isoformat()),
        ("Unknown", None),
    ]

    for label, ts in test_dates:
        score = score_recency(ts)
        print(f"  {label}: {score:.3f}")

    print("\n=== Type Scoring ===")
    for category in ["image", "pdf", "text", "audio", "video", "archive", "unknown"]:
        print(f"  {category}: {score_type(category):.2f}")

    print("\n=== Size Scoring ===")
    test_sizes = [
        ("10 KB", 10_000),
        ("100 KB", 100_000),
        ("1 MB", 1_000_000),
        ("10 MB", 10_000_000),
        ("50 MB", 50_000_000),
        ("100 MB", 100_000_000),
        ("500 MB", 500_000_000),
    ]
    for label, size in test_sizes:
        print(f"  {label}: {score_size(size):.2f}")
