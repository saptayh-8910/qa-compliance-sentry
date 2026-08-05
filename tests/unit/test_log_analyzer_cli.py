import json
from pathlib import Path

from typer.testing import CliRunner

from log_analyzer.cli import app

runner = CliRunner()


def test_cli_analyzes_file_and_writes_json_report(tmp_path: Path) -> None:
    log_path = tmp_path / "run.jsonl"
    report_path = tmp_path / "report.json"
    log_path.write_text(
        "\n".join(
            [
                '{"timestamp":"2026-08-04T03:00:00Z","level":"ERROR",'
                '"message":"timeout","test_name":"test_login"}',
                '{"timestamp":"2026-08-04T03:01:00Z","level":"ERROR",'
                '"message":"timeout","test_name":"test_checkout"}',
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "analyze",
            str(log_path),
            "--top",
            "1",
            "--output",
            str(report_path),
        ],
    )

    assert result.exit_code == 0
    assert "2 events: 2 failures, 1 incidents" in result.stdout
    assert "1. timeout (2)" in result.stdout
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["top_failures"][0]["signature"] == "timeout"


def test_cli_returns_error_for_missing_file(tmp_path: Path) -> None:
    result = runner.invoke(app, ["analyze", str(tmp_path / "missing.jsonl")])
    assert result.exit_code == 1
    assert "does not exist" in result.output
