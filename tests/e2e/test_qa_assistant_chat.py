from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.smoke, pytest.mark.chatbot]


def test_chatbot_supported_answer_abstention_and_exit(tmp_path: Path) -> None:
    guide = tmp_path / "quality-guide.md"
    guide.write_text(
        "# Pull request gates\n\nRuff and coverage run before merge.\n",
        encoding="utf-8",
    )
    project_root = Path(__file__).resolve().parents[2]

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "qa_assistant.cli",
            "chat",
            "--source",
            str(guide),
            "--top",
            "1",
        ],
        input="What runs before merge?\nphotosynthesis dinosaurs\nexit\n",
        text=True,
        capture_output=True,
        cwd=project_root,
        env={**os.environ, "NO_COLOR": "1"},
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Chat ready: indexed 1 documents into 1 chunks." in completed.stdout
    assert "Based on the retrieved documentation:" in completed.stdout
    assert "Ruff and coverage run before merge." in completed.stdout
    assert "[1]" in completed.stdout
    assert "quality-guide.md :: Pull request gates" in completed.stdout
    assert "could not find enough evidence" in completed.stdout
    assert completed.stdout.count("Sources:") == 1
    assert completed.stdout.count("Assistant:") == 2
    assert completed.stdout.rstrip().endswith("Chat ended.")
