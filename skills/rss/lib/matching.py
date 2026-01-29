"""RSS post matching against user explorations.

Matches new posts against active explorations to determine relevance.
Only relevant posts get surfaced to avoid overwhelming the user.
"""

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os


@dataclass
class MatchResult:
    """Result of matching a post against explorations."""
    matched: bool
    exploration_id: Optional[str] = None
    exploration_name: Optional[str] = None
    match_reason: str = ""
    score: float = 0.0
    details: dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


def _get_db_path() -> Path:
    """Get path to topics database."""
    data_dir = os.environ.get("EUNO_DATA_DIR")
    if data_dir:
        return Path(data_dir) / "topics" / "db.sqlite"
    return Path(__file__).parent.parent.parent.parent / "data" / "topics" / "db.sqlite"


def _tokenize(text: str) -> set[str]:
    """Extract meaningful tokens from text.

    Normalizes to lowercase, removes punctuation, filters short/common words.
    """
    if not text:
        return set()

    # Lowercase and split on non-word characters
    words = re.findall(r'\b[a-z]+\b', text.lower())

    # Extensive stop words list - be aggressive about filtering common words
    stop_words = {
        # Articles, conjunctions, prepositions
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'this', 'that', 'these', 'those', 'it', 'its', 'i', 'you', 'he', 'she',
        'we', 'they', 'what', 'which', 'who', 'whom', 'when', 'where', 'why',
        'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'not', 'only', 'own', 'same', 'so', 'than',
        'too', 'very', 'just', 'also', 'now', 'here', 'there', 'then', 'once',
        'about', 'into', 'over', 'after', 'before', 'between', 'under',
        'through', 'during', 'without', 'within', 'along', 'among', 'around',
        # Common verbs
        'get', 'got', 'getting', 'make', 'made', 'making', 'take', 'took',
        'taking', 'come', 'came', 'coming', 'go', 'went', 'going', 'know',
        'knew', 'knowing', 'think', 'thought', 'thinking', 'see', 'saw',
        'seeing', 'want', 'wanted', 'wanting', 'use', 'used', 'using',
        'find', 'found', 'finding', 'give', 'gave', 'giving', 'tell', 'told',
        'work', 'call', 'try', 'ask', 'seem', 'feel', 'leave', 'put', 'keep',
        'let', 'begin', 'show', 'hear', 'play', 'run', 'move', 'live', 'believe',
        # Common adjectives/adverbs
        'new', 'old', 'good', 'bad', 'big', 'small', 'long', 'short', 'high',
        'low', 'great', 'little', 'much', 'many', 'lot', 'first', 'last',
        'next', 'right', 'left', 'even', 'still', 'back', 'well', 'way',
        'really', 'already', 'almost', 'always', 'never', 'ever', 'often',
        # Common nouns that are too generic
        'thing', 'things', 'time', 'times', 'year', 'years', 'day', 'days',
        'week', 'month', 'people', 'person', 'man', 'woman', 'child', 'world',
        'life', 'hand', 'part', 'place', 'case', 'point', 'fact', 'group',
        'number', 'system', 'program', 'question', 'problem', 'kind', 'sort',
        'state', 'area', 'company', 'home', 'room', 'money', 'story', 'word',
        'side', 'line', 'end', 'head', 'water', 'face', 'house', 'night',
        'country', 'city', 'school', 'book', 'eye', 'job', 'business', 'issue',
        'government', 'service', 'information', 'power', 'result', 'idea',
        # Common words in blog posts
        'post', 'article', 'read', 'write', 'wrote', 'said', 'says', 'like',
        'today', 'yesterday', 'week', 'month', 'year', 'ago', 'via', 'update',
        'note', 'link', 'click', 'share', 'comment', 'reply', 'view', 'look',
        'looking', 'something', 'anything', 'nothing', 'everything', 'someone',
        'anyone', 'everyone', 'nobody', 'another', 'any', 'out', 'free',
        'media', 'news', 'report', 'says', 'according',
    }

    return {w for w in words if len(w) > 3 and w not in stop_words}


def _extract_themes(name: str, description: str = "") -> dict:
    """Extract themes and keywords from exploration name and description.

    Returns dict with:
    - keywords: set of individual important words
    - phrases: list of multi-word phrases to match
    - name_tokens: tokens from the name (higher weight)
    """
    name_tokens = _tokenize(name)
    desc_tokens = _tokenize(description or "")

    # Extract potential phrases (2-3 word sequences) from name
    name_lower = name.lower()
    # Remove common prefixes like "Explore", "Exploration"
    name_clean = re.sub(r'^(explore|exploration|exploring)\s*:?\s*', '', name_lower)

    # Split on punctuation to get phrase candidates
    phrase_parts = re.split(r'[:\-–—|/]', name_clean)
    phrases = [p.strip() for p in phrase_parts if len(p.strip()) > 3]

    return {
        "keywords": name_tokens | desc_tokens,
        "phrases": phrases,
        "name_tokens": name_tokens,
    }


def load_explorations() -> list[dict]:
    """Load active explorations from the database.

    Returns list of dicts with id, name, description, themes.
    """
    db_path = _get_db_path()
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Find the Explorations container
        cursor.execute(
            "SELECT id FROM topics WHERE name = 'Explorations' AND status != 'archived'"
        )
        container = cursor.fetchone()
        if not container:
            return []

        container_id = container["id"]

        # Get direct children of Explorations (the actual explorations)
        cursor.execute(
            """
            SELECT id, name, description
            FROM topics
            WHERE parent_id = ?
            AND status NOT IN ('archived', 'done')
            """,
            (container_id,)
        )

        explorations = []
        for row in cursor.fetchall():
            themes = _extract_themes(row["name"], row["description"])
            explorations.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"] or "",
                "themes": themes,
            })

        return explorations

    finally:
        conn.close()


def match_post(post: dict, explorations: list[dict] = None) -> MatchResult:
    """Match a post against active explorations.

    Args:
        post: Post dict with title, content_text, link
        explorations: Optional list of explorations (loads if not provided)

    Returns:
        MatchResult indicating if and why the post matched
    """
    if explorations is None:
        explorations = load_explorations()

    if not explorations:
        return MatchResult(
            matched=False,
            match_reason="No active explorations to match against",
        )

    post_title = post.get("title", "")
    post_content = post.get("content_text", "")
    post_text = f"{post_title} {post_content}".lower()
    post_tokens = _tokenize(post_text)

    best_match = None
    best_score = 0.0

    for exploration in explorations:
        themes = exploration["themes"]
        score = 0.0
        matched_items = []
        has_strong_match = False

        # Check phrase matches (highest weight, required for strong match)
        for phrase in themes["phrases"]:
            if phrase in post_text:
                score += 5.0
                matched_items.append(f"phrase '{phrase}'")
                has_strong_match = True

        # Check name token matches (high weight)
        # These are the core concept words from the exploration name
        name_overlap = themes["name_tokens"] & post_tokens
        if name_overlap:
            # Require at least 2 name keywords for it to count as strong
            if len(name_overlap) >= 2:
                score += len(name_overlap) * 2.0
                matched_items.append(f"name keywords: {', '.join(sorted(name_overlap))}")
                has_strong_match = True
            else:
                # Single name keyword is weak evidence
                score += len(name_overlap) * 0.5
                matched_items.append(f"weak: single name keyword '{list(name_overlap)[0]}'")

        # Check general keyword matches (lower weight, only counts if we have strong match)
        keyword_overlap = (themes["keywords"] - themes["name_tokens"]) & post_tokens
        if keyword_overlap and has_strong_match:
            # Only add description keywords if we already have a strong match
            score += min(len(keyword_overlap) * 0.3, 2.0)  # Cap contribution
            if len(keyword_overlap) <= 3:
                matched_items.append(f"supporting: {', '.join(sorted(keyword_overlap))}")
            else:
                matched_items.append(f"supporting: {len(keyword_overlap)} keywords")

        if score > best_score:
            best_score = score
            best_match = {
                "exploration": exploration,
                "score": score,
                "matched_items": matched_items,
                "has_strong_match": has_strong_match,
            }

    # Threshold for considering it a match
    # Require either a phrase match OR multiple name keyword matches
    if best_match and best_match.get("has_strong_match") and best_score >= 4.0:
        exp = best_match["exploration"]
        return MatchResult(
            matched=True,
            exploration_id=exp["id"],
            exploration_name=exp["name"],
            score=best_score,
            match_reason=f"Matched {', '.join(best_match['matched_items'])}",
            details={
                "score": best_score,
                "matched_items": best_match["matched_items"],
                "post_title": post_title,
            },
        )

    reason = f"No strong match (best score: {best_score:.1f}, need 4.0 with phrase/multi-keyword)"
    if best_match and not best_match.get("has_strong_match"):
        reason = f"No phrase or multi-keyword match (score: {best_score:.1f})"

    return MatchResult(
        matched=False,
        match_reason=reason,
        score=best_score,
        details={
            "best_score": best_score,
            "threshold": 4.0,
            "requires": "phrase match OR 2+ name keywords",
            "explorations_checked": [e["name"] for e in explorations],
            "post_title": post_title,
        },
    )


def analyze_feed_matches(posts: list[dict], explorations: list[dict] = None) -> dict:
    """Analyze how posts from a feed match against explorations.

    Useful for debugging and understanding match behavior.

    Args:
        posts: List of posts to analyze
        explorations: Optional explorations list

    Returns:
        Dict with match statistics and details
    """
    if explorations is None:
        explorations = load_explorations()

    results = {
        "total_posts": len(posts),
        "matched_posts": 0,
        "unmatched_posts": 0,
        "explorations": [e["name"] for e in explorations],
        "matches": [],
        "non_matches": [],
    }

    for post in posts:
        result = match_post(post, explorations)
        if result.matched:
            results["matched_posts"] += 1
            results["matches"].append({
                "title": post.get("title"),
                "exploration": result.exploration_name,
                "reason": result.match_reason,
                "score": result.score,
            })
        else:
            results["unmatched_posts"] += 1
            results["non_matches"].append({
                "title": post.get("title"),
                "reason": result.match_reason,
                "score": result.score,
            })

    return results
