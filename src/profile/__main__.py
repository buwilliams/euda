"""
CLI interface for Euno profile operations.

Usage:
    python -m src.profile validate <path>
    python -m src.profile make-public <private_path> [output_dir]
    python -m src.profile show-contract
    python -m src.profile show-policy
    python -m src.profile show-prefs
"""

import sys
from pathlib import Path

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent / "data"
SHARED_DIR = DATA_DIR / "shared"
SYNTHESIS_DIR = DATA_DIR / "synthesis"
PROFILE_DIR = SYNTHESIS_DIR / "profile"  # User profile data lives under synthesis
CONTRACT_DIR = SHARED_DIR / "profile"    # System config (contract, policy)


def cmd_validate(args: list[str]) -> int:
    """Validate a profile file."""
    if len(args) < 1:
        print("Usage: python -m src.profile validate <path>")
        return 1

    from .validate import validate_profile

    path = args[0]
    result = validate_profile(path)

    if result.warnings:
        print("Warnings:")
        for w in result.warnings:
            print(f"  - {w}")

    if result.errors:
        print("Errors:")
        for e in result.errors:
            print(f"  - {e}")
        return 1
    else:
        print("Profile is valid.")
        return 0


def cmd_make_public(args: list[str]) -> int:
    """Generate a public profile from a private profile."""
    if len(args) < 1:
        print("Usage: python -m src.profile make-public <private_path> [output_dir]")
        return 1

    from .generate import generate_public_profile

    private_path = args[0]
    output_dir = args[1] if len(args) > 1 else None

    print(f"Generating public profile from: {private_path}")
    if output_dir:
        print(f"Output directory: {output_dir}")

    result = generate_public_profile(private_path, output_dir)

    if result.success:
        print("\nPublic profile generated successfully.")
        print("\nFiles written:")
        for f in result.files_written:
            print(f"  - {f}")
        if result.validation and result.validation.warnings:
            print("\nWarnings:")
            for w in result.validation.warnings:
                print(f"  - {w}")
        return 0
    else:
        print(f"\nGeneration failed: {result.error}")
        if result.validation and result.validation.errors:
            print("\nValidation errors:")
            for e in result.validation.errors:
                print(f"  - {e}")
        return 1


def cmd_show_contract(args: list[str]) -> int:
    """Display the profile contract."""
    contract_path = CONTRACT_DIR / "profile.contract.md"
    if not contract_path.exists():
        print(f"Profile contract not found: {contract_path}")
        return 1

    print(contract_path.read_text())
    return 0


def cmd_show_policy(args: list[str]) -> int:
    """Display the redaction policy."""
    policy_path = CONTRACT_DIR / "redaction.policy.md"
    if not policy_path.exists():
        print(f"Redaction policy not found: {policy_path}")
        return 1

    print(policy_path.read_text())
    return 0


def cmd_show_prefs(args: list[str]) -> int:
    """Display current sharing preferences."""
    prefs_path = PROFILE_DIR / "share.prefs.current.md"
    if not prefs_path.exists():
        template_path = PROFILE_DIR / "share.prefs.template.md"
        if template_path.exists():
            print("(No current preferences, showing template)\n")
            print(template_path.read_text())
            return 0
        print("No sharing preferences found.")
        return 1

    print(prefs_path.read_text())
    return 0


def cmd_help(args: list[str]) -> int:
    """Show help."""
    print(__doc__)
    print("\nCommands:")
    print("  validate <path>          Validate a profile file")
    print("  make-public <path> [dir] Generate public profile from private")
    print("  show-contract            Display the profile contract")
    print("  show-policy              Display the redaction policy")
    print("  show-prefs               Display current sharing preferences")
    print("  help                     Show this help message")
    return 0


COMMANDS = {
    "validate": cmd_validate,
    "make-public": cmd_make_public,
    "show-contract": cmd_show_contract,
    "show-policy": cmd_show_policy,
    "show-prefs": cmd_show_prefs,
    "help": cmd_help,
}


def main():
    if len(sys.argv) < 2:
        cmd_help([])
        sys.exit(0)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command not in COMMANDS:
        print(f"Unknown command: {command}")
        print("Use 'help' for available commands.")
        sys.exit(1)

    sys.exit(COMMANDS[command](args))


if __name__ == "__main__":
    main()
