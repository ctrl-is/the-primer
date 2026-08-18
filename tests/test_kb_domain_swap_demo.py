from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_kb_domain_swap_demo_exits_zero() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    # sys.executable resolves inside the uv-managed venv pytest runs in, so the demo
    # sees the same environment as `uv run python demos/kb_domain_swap.py`.
    result = subprocess.run(
        [sys.executable, "demos/kb_domain_swap.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "education" in result.stdout
    assert "coop-finance" in result.stdout
    assert "Zero engine branching: PASS" in result.stdout
