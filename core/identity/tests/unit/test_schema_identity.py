import json
from pathlib import Path

import pytest

from src import cli
from conftest import DEFAULT_TRAITS, write_schema


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_versioning(identity_env):
    data_dir = identity_env / "data"
    payload = json.dumps(DEFAULT_TRAITS)

    cli.schema_create("alpha", payload)
    cli.schema_create("alpha", payload)

    schema_dir = data_dir / "schema"
    v1 = _load(schema_dir / "alpha-1.json")
    v2 = _load(schema_dir / "alpha-2.json")

    assert v1["version"] == 1
    assert v2["version"] == 2
    assert v1["schema_id"] == v2["schema_id"]


def test_identity_versioning(identity_env):
    data_dir = identity_env / "data"
    write_schema(data_dir)

    cli.identity_create("neo", "## Purpose\nOne\n", schema="cognitive-core", schema_version=None)
    cli.identity_create("neo", "## Purpose\nTwo\n", schema="cognitive-core", schema_version=None)

    identity_dir = data_dir / "identity" / "cognitive-core"
    v1 = _load(identity_dir / "neo-1.json")
    v2 = _load(identity_dir / "neo-2.json")

    assert v1["version"] == 1
    assert v2["version"] == 2
    assert v1["content"].strip() == "## Purpose\nOne"
    assert v2["content"].strip() == "## Purpose\nTwo"
