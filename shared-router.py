import json
import subprocess
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class CliResult:
    stdout: str
    stderr: str
    returncode: int


class CliError(RuntimeError):
    pass


def run_cli(
    command: Sequence[str],
    *,
    input_text: str | None = None,
    timeout: float | None = 30.0,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
) -> CliResult:
    result = subprocess.run(
        list(command),
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        cwd=cwd,
        env=env,
    )
    return CliResult(stdout=result.stdout, stderr=result.stderr, returncode=result.returncode)


def run_cli_or_raise(
    command: Sequence[str],
    *,
    input_text: str | None = None,
    timeout: float | None = 30.0,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
) -> CliResult:
    result = run_cli(
        command,
        input_text=input_text,
        timeout=timeout,
        cwd=cwd,
        env=env,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Command failed"
        raise CliError(f"{command[0]} failed ({result.returncode}): {message}")
    return result


def run_cli_json(
    command: Sequence[str],
    *,
    input_text: str | None = None,
    timeout: float | None = 30.0,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
) -> Any:
    result = run_cli_or_raise(
        command,
        input_text=input_text,
        timeout=timeout,
        cwd=cwd,
        env=env,
    )
    return json.loads(result.stdout)


def run_euda(
    args: Sequence[str],
    *,
    input_text: str | None = None,
    timeout: float | None = 30.0,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
) -> CliResult:
    return run_cli_or_raise(
        ["uv", "run", "euda", *args],
        input_text=input_text,
        timeout=timeout,
        cwd=cwd,
        env=env,
    )


def run_euda_json(
    args: Sequence[str],
    *,
    input_text: str | None = None,
    timeout: float | None = 30.0,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
) -> Any:
    result = run_euda(
        args,
        input_text=input_text,
        timeout=timeout,
        cwd=cwd,
        env=env,
    )
    return json.loads(result.stdout)
