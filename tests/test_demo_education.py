from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_education_demo_exits_zero() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    # sys.executable resolves inside the uv-managed venv pytest runs in, so the demo
    # sees the same environment as `uv run python demos/demo_education.py`.
    result = subprocess.run(
        [sys.executable, "demos/demo_education.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "DEMO SUCCESS" in result.stdout
