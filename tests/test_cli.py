from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cli_transpile_to_file(tmp_path: Path) -> None:
    dsl_path = Path("examples/erc20.dsl")
    out_path = tmp_path / "ERC20.sol"

    result = subprocess.run(
        [sys.executable, "-m", "snakechain", str(dsl_path), "-o", str(out_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    rendered = out_path.read_text()
    assert "contract ERC20" in rendered
    assert "function transfer(address to, uint256 amount) public" in rendered


def test_cli_transpile_stdout(tmp_path: Path) -> None:
    dsl_path = Path("examples/erc20.dsl")

    result = subprocess.run(
        [sys.executable, "-m", "snakechain", str(dsl_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "contract ERC20" in result.stdout
    assert "function transfer(address to, uint256 amount) public" in result.stdout
    assert result.stderr == ""
