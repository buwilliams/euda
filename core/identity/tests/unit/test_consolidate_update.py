import json
from dataclasses import dataclass
from pathlib import Path

import pytest
import typer

from src import cli
from conftest import DEFAULT_TRAITS, write_schema


@dataclass
class StubResult:
    stdout: str
    stderr: str = ""
    returncode: int = 0


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _markdown_from_traits(body: str = "Updated") -> str:
    parts = []
    for trait in DEFAULT_TRAITS:
        parts.append(f"## {trait['name']}")
        parts.append(body)
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def test_consolidate_without_memory(identity_env, monkeypatch):
    data_dir = identity_env / "data"
    write_schema(data_dir)

    def stub_run_core(app, args, input_text=None, **kwargs):
        raise AssertionError("LLM should not be called when there are no sources")

    monkeypatch.setattr(cli.shared_router, "run_core", stub_run_core)

    cli.consolidate(
        "neo",
        schema="cognitive-core",
        schema_version=None,
        memory_term=None,
        memory_type=None,
        memory_id=None,
        input_text=[],
        years=None,
        days=None,
        hours=None,
        max_chars=20000,
        summary_max_chars=8000,
        provider=None,
        model=None,
        retries=0,
        retry_wait=0.0,
        llm_timeout=1.0,
        no_stdin=True,
        no_topics=True,
        no_input=True,
        no_memory=True,
        no_previous=True,
    )

    identity_dir = data_dir / "identity" / "cognitive-core"
    payload = _load(identity_dir / "neo-1.json")
    assert "## Purpose" in payload["content"]


def test_consolidate_memory_partial_error(identity_env):
    data_dir = identity_env / "data"
    write_schema(data_dir)

    with pytest.raises(typer.Exit) as exc:
        cli.consolidate(
            "neo",
            schema="cognitive-core",
            schema_version=None,
            memory_term="short",
            memory_type=None,
            memory_id=None,
            input_text=[],
            years=None,
            days=None,
            hours=None,
            max_chars=20000,
            summary_max_chars=8000,
            provider=None,
            model=None,
            retries=0,
            retry_wait=0.0,
            llm_timeout=1.0,
            no_memory=False,
            no_topics=True,
            no_input=True,
            no_stdin=True,
        )
    assert exc.value.exit_code == 1


def test_update_in_place_with_input(identity_env, monkeypatch):
    data_dir = identity_env / "data"
    write_schema(data_dir)
    cli.identity_create("neo", "## Purpose\nSeed\n", schema="cognitive-core", schema_version=None)

    expected = _markdown_from_traits()

    def stub_run_core(app, args, input_text=None, **kwargs):
        if app == "llm":
            return StubResult(stdout=expected)
        if app == "topics":
            return StubResult(stdout="")
        if app == "memory":
            return StubResult(stdout="")
        raise AssertionError(f"unexpected app: {app}")

    monkeypatch.setattr(cli.shared_router, "run_core", stub_run_core)

    identity_dir = data_dir / "identity" / "cognitive-core"
    before = _load(identity_dir / "neo-1.json")

    cli.update(
        "neo",
        schema="cognitive-core",
        memory_term=None,
        memory_type=None,
        memory_id=None,
        input_text=["signal"],
        years=None,
        days=None,
        hours=None,
        max_chars=20000,
        summary_max_chars=8000,
        provider=None,
        model=None,
        retries=0,
        retry_wait=0.0,
        llm_timeout=1.0,
        no_stdin=True,
        no_topics=True,
        no_input=False,
        no_memory=True,
        include_history=False,
    )

    after = _load(identity_dir / "neo-1.json")

    assert after["version"] == before["version"]
    assert after["content"].strip() == expected.strip()
    assert after["updated_at"] != before["updated_at"]
    assert "updates" in after.get("metadata", {})
    assert len(after["metadata"]["updates"]) == 1
