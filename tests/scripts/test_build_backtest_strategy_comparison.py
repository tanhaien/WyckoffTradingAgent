from __future__ import annotations

import sys
from pathlib import Path

from scripts.build_backtest_strategy_comparison import main


def test_require_complete_returns_failure_after_writing_report(tmp_path: Path, monkeypatch) -> None:
    markdown = tmp_path / "report.md"
    json_output = tmp_path / "report.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_backtest_strategy_comparison.py",
            "--artifacts-dir",
            str(tmp_path),
            "--markdown-output",
            str(markdown),
            "--json-output",
            str(json_output),
            "--require-complete",
        ],
    )

    assert main() == 1
    assert "证据不完整" in markdown.read_text(encoding="utf-8")
    assert '"status": "incomplete"' in json_output.read_text(encoding="utf-8")
