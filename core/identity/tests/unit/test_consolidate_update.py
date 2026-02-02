import json
from dataclasses import dataclass

import pytest
import typer

from src import cli
from tests.unit.conftest import write_guide, write_identity


@dataclass
class StubResult:
    stdout: str
    stderr: str = ""
    returncode: int = 0


def test_consolidate_rejects_large_change(identity_env, monkeypatch):
    data_dir = identity_env / "data"
    write_guide(data_dir)
    write_identity(data_dir, name="neo")

    override = {
        "consolidate": {"max_change_ratio": 0.01},
    }
    (identity_env / "config.json").write_text(
        json.dumps(override, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    def stub_run_core(app_name, args, input_text=None, **kwargs):
        return StubResult(stdout="# neo\n\n## Purpose\nCompletely different\n")

    monkeypatch.setattr(cli.shared_router, "run_core", stub_run_core)

    with pytest.raises(typer.Exit):
        cli.consolidate(
            "neo",
            input_file=[],
            input_text=["signal"],
            no_stdin=True,
            provider=None,
            model=None,
            llm_timeout=1.0,
        )


def test_prune_versions(identity_env):
    data_dir = identity_env / "data"
    write_guide(data_dir)

    override = {
        "identity": {"max_versions": 2}
    }
    (identity_env / "config.json").write_text(
        json.dumps(override, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    cli.identity_create("neo", "# neo\n\n## Purpose\nOne\n", file=None)
    cli.identity_write("neo", "# neo\n\n## Purpose\nTwo\n", from_version=None, file=None)
    cli.identity_write("neo", "# neo\n\n## Purpose\nThree\n", from_version=None, file=None)

    identity_dir = data_dir / "identity" / "neo"
    assert not (identity_dir / "identity-1.md").exists()
    assert (identity_dir / "identity-2.md").exists()
    assert (identity_dir / "identity-3.md").exists()
