import json
from pathlib import Path

from src import cli
from tests.unit.conftest import write_guide


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_guide_versioning(identity_env):
    data_dir = identity_env / "data"

    cli.guide_write("# guide one", from_version=None, file=None)
    cli.guide_write("# guide two", from_version=None, file=None)

    guide_dir = data_dir / "guide"
    v1 = _load(guide_dir / "guide-1.json")
    v2 = _load(guide_dir / "guide-2.json")

    assert v1["version"] == 1
    assert v2["version"] == 2


def test_identity_versioning(identity_env):
    data_dir = identity_env / "data"
    write_guide(data_dir)

    cli.identity_create("neo", "# neo\n\n## Purpose\nOne\n", file=None)
    cli.identity_write("neo", "# neo\n\n## Purpose\nTwo\n", from_version=None, file=None)
    identity_dir = data_dir / "identity" / "neo"
    v1 = _load(identity_dir / "identity-1.json")
    v2 = _load(identity_dir / "identity-2.json")

    assert v1["version"] == 1
    assert v2["version"] == 2
    assert (identity_dir / "identity-1.md").read_text(encoding="utf-8").strip().endswith("One")
    assert (identity_dir / "identity-2.md").read_text(encoding="utf-8").strip().endswith("Two")
