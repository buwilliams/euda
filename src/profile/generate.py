"""
Public profile generation for Euno.

Pipeline:
1. Load private profile, contract, redaction policy, and user preferences
2. Call LLM to select and rewrite content for public sharing
3. Validate the generated output
4. Write public profile files if validation passes

LLM is responsible for inclusion decisions.
Python enforces artifact-class boundaries.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..providers import get_provider, get_provider_config
from .validate import validate_profile, ValidationResult


# Base paths
DATA_DIR = Path(__file__).parent.parent.parent / "data"
SHARED_DIR = DATA_DIR / "shared"
SYNTHESIS_DIR = DATA_DIR / "synthesis"
PROFILE_DIR = SYNTHESIS_DIR / "state" / "profile"  # User profile data lives under synthesis
CONTRACT_DIR = SHARED_DIR / "state" / "profile"    # System config (contract, policy)


@dataclass
class GenerationResult:
    """Result of public profile generation."""
    success: bool
    public_profile: Optional[str] = None
    validation: Optional[ValidationResult] = None
    error: Optional[str] = None
    files_written: list[str] = None

    def __post_init__(self):
        if self.files_written is None:
            self.files_written = []


def load_contract() -> str:
    """Load the profile contract."""
    contract_path = CONTRACT_DIR / "profile.contract.md"
    if not contract_path.exists():
        raise FileNotFoundError(f"Profile contract not found: {contract_path}")
    return contract_path.read_text()


def load_redaction_policy() -> str:
    """Load the redaction policy."""
    policy_path = CONTRACT_DIR / "redaction.policy.md"
    if not policy_path.exists():
        raise FileNotFoundError(f"Redaction policy not found: {policy_path}")
    return policy_path.read_text()


def load_share_prefs() -> str:
    """Load user sharing preferences."""
    prefs_path = PROFILE_DIR / "share.prefs.current.md"
    if not prefs_path.exists():
        # Fall back to template
        template_path = PROFILE_DIR / "share.prefs.template.md"
        if template_path.exists():
            return template_path.read_text()
        return "No sharing preferences configured."
    return prefs_path.read_text()


def build_generation_prompt(
    private_profile: str,
    contract: str,
    policy: str,
    prefs: str,
    source_path: str
) -> str:
    """Build the prompt for public profile generation."""
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    year = datetime.now().strftime("%Y")

    return f"""You are generating a public profile from a private profile.

## Your Task

Transform the private profile into a public profile that:
1. Follows the profile contract structure exactly
2. Adheres to the redaction policy
3. Respects the user's sharing preferences
4. Contains NO forbidden artifact types (quotes, transcripts, raw logs, excerpts)

## Documents

### Profile Contract
{contract}

### Redaction Policy
{policy}

### User Sharing Preferences
{prefs}

### Private Profile (Source)
{private_profile}

## Output Requirements

Generate a complete public profile that:

1. **Begins with valid JSON frontmatter** (as a ```json code block):
```json
{{
  "profile_version": "1.0",
  "scope": "public",
  "generated_at": "{timestamp}",
  "source_profile": "{source_path}"
}}
```

2. **Contains sections in canonical order** (omit empty sections):
   - Identity Constraints
   - Failure Modes
   - Behavioral Attractors
   - Utility Tradeoff Curves
   - Epistemic Style
   - Narrative Identity

3. **Uses the profile item microformat** where applicable:
```markdown
- **[Label]**: [Description]
  - Evidence: [category only, no excerpts]
  - Confidence: [high | medium | low]
  - Last observed: [YYYY or YYYY-MM]
```

4. **Contains NO forbidden content:**
   - No direct quotes from private sources
   - No transcript markers
   - No raw log entries
   - No excerpts
   - No third-party identifying information
   - No precise locations, financial details, or health specifics

5. **Applies generalization:**
   - Abstract patterns, not specific events
   - Categories of evidence, not file paths
   - Time ranges, not exact dates
   - Regions, not addresses

## Critical Rules

- **Structure over story**: Describe patterns, not narratives
- **Omission over exposure**: When uncertain, leave it out
- **Evidence pointers only**: Never reproduce source content
- **User preferences override defaults**: But cannot override hard constraints

## Output

Output ONLY the public profile markdown. No preamble, no explanation.
Begin with the JSON frontmatter code block (```json)."""


def call_llm(prompt: str) -> str:
    """Call the LLM to generate the public profile."""
    provider = get_provider()
    config = get_provider_config()
    model = config.get("default_model", "claude-sonnet-4-20250514")
    max_tokens = config.get("max_tokens", 8096)

    response = provider.create_message(
        model=model,
        system="You are a profile transformation specialist. You convert private profiles into safe public profiles following strict structural and content rules.",
        messages=[{"role": "user", "content": prompt}],
        tools=None,
        max_tokens=max_tokens
    )

    # Extract text from response
    return "\n".join(response.text_blocks)


def write_public_profiles(content: str, output_dir: Path) -> list[str]:
    """
    Write public profile files.

    Creates:
    - profile.public.current.md
    - profile.public.YYYY.md

    Returns list of written file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    year = datetime.now().strftime("%Y")

    files = []

    # Write current
    current_path = output_dir / "profile.public.current.md"
    current_path.write_text(content)
    files.append(str(current_path))

    # Write year snapshot
    year_path = output_dir / f"profile.public.{year}.md"
    year_path.write_text(content)
    files.append(str(year_path))

    return files


def generate_public_profile(
    private_path: str | Path,
    output_dir: Optional[str | Path] = None,
    prefs_path: Optional[str | Path] = None
) -> GenerationResult:
    """
    Generate a public profile from a private profile.

    Args:
        private_path: Path to the private profile
        output_dir: Directory for output files (default: data/profile/)
        prefs_path: Path to sharing preferences (default: data/profile/share.prefs.current.md)

    Returns:
        GenerationResult with success status and any errors
    """
    private_path = Path(private_path)
    output_dir = Path(output_dir) if output_dir else PROFILE_DIR

    # Validate private profile first
    private_validation = validate_profile(private_path, expected_scope="private")
    if not private_validation.valid:
        return GenerationResult(
            success=False,
            error=f"Private profile validation failed: {'; '.join(private_validation.errors)}",
            validation=private_validation
        )

    # Load all required documents
    try:
        private_profile = private_path.read_text()
        contract = load_contract()
        policy = load_redaction_policy()

        if prefs_path:
            prefs = Path(prefs_path).read_text()
        else:
            prefs = load_share_prefs()
    except FileNotFoundError as e:
        return GenerationResult(
            success=False,
            error=f"Required file not found: {e}"
        )

    # Build prompt and call LLM
    prompt = build_generation_prompt(
        private_profile=private_profile,
        contract=contract,
        policy=policy,
        prefs=prefs,
        source_path=str(private_path)
    )

    try:
        public_profile = call_llm(prompt)
    except Exception as e:
        return GenerationResult(
            success=False,
            error=f"LLM call failed: {e}"
        )

    # Write to temp file for validation
    temp_path = output_dir / ".profile.public.temp.md"
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(public_profile)

    # Validate generated profile
    validation = validate_profile(temp_path, expected_scope="public")

    # Clean up temp file
    temp_path.unlink()

    if not validation.valid:
        return GenerationResult(
            success=False,
            public_profile=public_profile,
            validation=validation,
            error=f"Generated profile validation failed: {'; '.join(validation.errors)}"
        )

    # Write final files
    files_written = write_public_profiles(public_profile, output_dir)

    return GenerationResult(
        success=True,
        public_profile=public_profile,
        validation=validation,
        files_written=files_written
    )


# CLI support
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.profile.generate <private_profile_path> [output_dir]")
        sys.exit(1)

    private_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    result = generate_public_profile(private_path, output_dir)

    if result.success:
        print("Public profile generated successfully.")
        print("Files written:")
        for f in result.files_written:
            print(f"  - {f}")
        if result.validation and result.validation.warnings:
            print("Warnings:")
            for w in result.validation.warnings:
                print(f"  - {w}")
    else:
        print(f"Generation failed: {result.error}")
        if result.validation and result.validation.errors:
            print("Validation errors:")
            for e in result.validation.errors:
                print(f"  - {e}")
        sys.exit(1)
