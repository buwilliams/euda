from typer.testing import CliRunner
from main import app


def test_ping():
    runner = CliRunner()
    result = runner.invoke(app, ["ping"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "pong"
