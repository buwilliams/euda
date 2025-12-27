"""
Profile validation for Euno.

Validates ONLY structural requirements:
- JSON frontmatter presence and correctness
- Section presence and order per contract
- Profile item microformat compliance
- Absence of forbidden artifact types (public only)

This validator checks structure, not meaning.
LLMs are responsible for content judgment.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ValidationResult:
    """Result of profile validation."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.valid = False

    def add_warning(self, msg: str):
        self.warnings.append(msg)


# Canonical section order from profile.contract.md
CANONICAL_SECTIONS = [
    "Identity Constraints",
    "Failure Modes",
    "Behavioral Attractors",
    "Utility Tradeoff Curves",
    "Epistemic Style",
    "Narrative Identity",
]

# Required frontmatter fields
REQUIRED_FRONTMATTER = ["profile_version", "scope", "generated_at"]

# Additional required field for public profiles
PUBLIC_REQUIRED_FRONTMATTER = ["source_profile"]

# Forbidden patterns in public profiles (artifact-class boundaries)
# These detect structural markers, not content
FORBIDDEN_PATTERNS_PUBLIC = [
    # Direct quotes (text in quotation marks that looks like speech)
    (r'"[^"]{50,}"', "Direct quote detected (long quoted text)"),
    (r"'[^']{50,}'", "Direct quote detected (long single-quoted text)"),

    # Transcript markers
    (r"^\s*\[[^\]]+\]:\s*", "Transcript marker detected ([Speaker]:)"),
    (r"^\s*[A-Z][a-z]+:\s+[\"']", "Transcript marker detected (Name: \"...)"),

    # Raw log markers
    (r"^---\n\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "Raw log entry detected (timestamped entry)"),
    (r"^Entry from \d{4}-\d{2}-\d{2}", "Raw log reference detected"),

    # Excerpt markers
    (r"from (?:my )?(?:journal|diary|notes|log).*:", "Excerpt reference detected"),
    (r"I (?:wrote|said|recorded).*:", "First-person excerpt marker detected"),
]


def extract_frontmatter(content: str) -> tuple[Optional[dict], str]:
    """
    Extract JSON frontmatter from markdown content.

    Frontmatter is expected as a ```json code block at the start of the file.

    Returns:
        Tuple of (frontmatter dict or None, remaining content)
    """
    # Check for JSON code block at start
    if not content.startswith("```json"):
        return None, content

    # Find the closing ```
    lines = content.split("\n")
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "```":
            end_idx = i
            break

    if end_idx is None:
        return None, content

    # Parse JSON
    json_content = "\n".join(lines[1:end_idx])
    try:
        frontmatter = json.loads(json_content)
        remaining = "\n".join(lines[end_idx + 1:])
        return frontmatter, remaining
    except json.JSONDecodeError:
        return None, content


def extract_sections(content: str) -> list[tuple[str, str]]:
    """
    Extract H2 sections from markdown content.

    Returns:
        List of (section_name, section_content) tuples
    """
    sections = []
    current_section = None
    current_content = []

    for line in content.split("\n"):
        if line.startswith("## "):
            # Save previous section
            if current_section is not None:
                sections.append((current_section, "\n".join(current_content)))
            # Start new section
            current_section = line[3:].strip()
            current_content = []
        elif current_section is not None:
            current_content.append(line)

    # Save final section
    if current_section is not None:
        sections.append((current_section, "\n".join(current_content)))

    return sections


def validate_frontmatter(frontmatter: Optional[dict], scope: str) -> ValidationResult:
    """Validate frontmatter against requirements."""
    result = ValidationResult(valid=True)

    if frontmatter is None:
        result.add_error("Missing JSON frontmatter (must start with ```json block)")
        return result

    # Check required fields
    for field in REQUIRED_FRONTMATTER:
        if field not in frontmatter:
            result.add_error(f"Missing required frontmatter field: {field}")

    # Check scope value
    if "scope" in frontmatter:
        if frontmatter["scope"] not in ["private", "public"]:
            result.add_error(f"Invalid scope: {frontmatter['scope']} (must be 'private' or 'public')")

    # Check public-specific requirements
    if scope == "public" or (frontmatter and frontmatter.get("scope") == "public"):
        for field in PUBLIC_REQUIRED_FRONTMATTER:
            if field not in frontmatter:
                result.add_error(f"Missing required frontmatter field for public profile: {field}")

    # Check profile_version format
    if "profile_version" in frontmatter:
        version = str(frontmatter["profile_version"])
        if not re.match(r"^\d+\.\d+$", version):
            result.add_warning(f"Unusual profile_version format: {version}")

    return result


def validate_section_order(sections: list[tuple[str, str]]) -> ValidationResult:
    """Validate that sections appear in canonical order."""
    result = ValidationResult(valid=True)

    section_names = [name for name, _ in sections]

    # Find which canonical sections are present
    present_canonical = [s for s in CANONICAL_SECTIONS if s in section_names]

    # Check that present sections are in order
    last_idx = -1
    for section in present_canonical:
        idx = CANONICAL_SECTIONS.index(section)
        if idx < last_idx:
            result.add_error(f"Section '{section}' is out of order (should come before previous section)")
        last_idx = idx

    # Warn about non-canonical sections
    for name in section_names:
        if name not in CANONICAL_SECTIONS:
            result.add_warning(f"Non-canonical section: '{name}'")

    return result


def validate_forbidden_patterns(content: str) -> ValidationResult:
    """
    Check for forbidden artifact types in public profiles.

    This is a structural check, not content detection.
    It looks for markers that indicate raw logs, quotes, or transcripts.
    """
    result = ValidationResult(valid=True)

    for pattern, description in FORBIDDEN_PATTERNS_PUBLIC:
        matches = re.findall(pattern, content, re.MULTILINE)
        if matches:
            result.add_error(f"Forbidden artifact type: {description}")

    return result


def validate_profile(path: str | Path, expected_scope: Optional[str] = None) -> ValidationResult:
    """
    Validate a profile file against the profile contract.

    Args:
        path: Path to the profile file
        expected_scope: Expected scope ("private" or "public"), inferred if not provided

    Returns:
        ValidationResult with errors and warnings
    """
    path = Path(path)
    result = ValidationResult(valid=True)

    # Check file exists
    if not path.exists():
        result.add_error(f"Profile file does not exist: {path}")
        return result

    # Read content
    try:
        content = path.read_text()
    except Exception as e:
        result.add_error(f"Could not read file: {e}")
        return result

    # Extract frontmatter
    frontmatter, body = extract_frontmatter(content)

    # Determine scope
    if expected_scope is None:
        if frontmatter and "scope" in frontmatter:
            expected_scope = frontmatter["scope"]
        elif "public" in path.name.lower():
            expected_scope = "public"
        else:
            expected_scope = "private"

    # Validate frontmatter
    fm_result = validate_frontmatter(frontmatter, expected_scope)
    result.errors.extend(fm_result.errors)
    result.warnings.extend(fm_result.warnings)
    if not fm_result.valid:
        result.valid = False

    # Extract and validate sections
    sections = extract_sections(body)
    section_result = validate_section_order(sections)
    result.errors.extend(section_result.errors)
    result.warnings.extend(section_result.warnings)
    if not section_result.valid:
        result.valid = False

    # For public profiles, check for forbidden patterns
    if expected_scope == "public":
        pattern_result = validate_forbidden_patterns(body)
        result.errors.extend(pattern_result.errors)
        result.warnings.extend(pattern_result.warnings)
        if not pattern_result.valid:
            result.valid = False

    return result


# CLI support
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.profile.validate <profile_path>")
        sys.exit(1)

    result = validate_profile(sys.argv[1])

    if result.warnings:
        print("Warnings:")
        for w in result.warnings:
            print(f"  - {w}")

    if result.errors:
        print("Errors:")
        for e in result.errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("Profile is valid.")
        sys.exit(0)
