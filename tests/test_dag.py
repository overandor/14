from __future__ import annotations

from pathlib import Path

import pytest

from snakechain import DagConfigError, DagExecutionError, RealizationDagRunner, load_pipeline


def _write_pipeline(tmp: Path, steps: str) -> Path:
    path = tmp / "pipeline.yaml"
    path.write_text(steps, encoding="utf-8")
    return path


def test_load_pipeline_enforces_required_order(tmp_path: Path):
    path = _write_pipeline(
        tmp_path,
        """
steps:
  - name: fetch_data
    type: fetch_data
    command: "echo fetch"
  - name: human_gate
    type: human_gate
    command: "echo gate"
    proof_path: proof.txt
  - name: signal_generator
    type: signal_generator
    command: "echo signal"
  - name: profit_evaluator
    type: profit_evaluator
    command: "echo eval"
""",
    )

    steps = load_pipeline(path)
    assert [step.type.value for step in steps] == [
        "fetch_data",
        "human_gate",
        "signal_generator",
        "profit_evaluator",
    ]


def test_load_pipeline_rejects_wrong_order(tmp_path: Path):
    path = _write_pipeline(
        tmp_path,
        """
steps:
  - name: profit_evaluator
    type: profit_evaluator
    command: "echo eval"
""",
    )

    with pytest.raises(DagConfigError):
        load_pipeline(path)


def test_runner_requires_proof(tmp_path: Path):
    proof = tmp_path / "proof.txt"
    pipeline = _write_pipeline(
        tmp_path,
        f"""
steps:
  - name: fetch_data
    type: fetch_data
    command: "echo fetch"
  - name: human_gate
    type: human_gate
    command: "echo gate"
    proof_path: {proof}
  - name: signal_generator
    type: signal_generator
    command: "echo signal"
  - name: profit_evaluator
    type: profit_evaluator
    command: "echo eval"
""",
    )

    steps = load_pipeline(pipeline)
    runner = RealizationDagRunner(steps)
    with pytest.raises(DagExecutionError):
        runner.run()


def test_runner_executes_when_proof_present(tmp_path: Path):
    proof = tmp_path / "proof.txt"
    proof.write_text("approved", encoding="utf-8")

    pipeline = _write_pipeline(
        tmp_path,
        f"""
steps:
  - name: fetch_data
    type: fetch_data
    command: |
      python -c "from pathlib import Path; Path('{tmp_path}/data.json').write_text('1', encoding='utf-8')"
  - name: human_gate
    type: human_gate
    command: "echo gate"
    proof_path: {proof}
    expected_token: approved
  - name: signal_generator
    type: signal_generator
    command: |
      python -c "from pathlib import Path; assert Path('{tmp_path}/data.json').exists(); Path('{tmp_path}/signal.json').write_text('hold', encoding='utf-8')"
  - name: profit_evaluator
    type: profit_evaluator
    command: |
      python -c "from pathlib import Path; assert Path('{tmp_path}/signal.json').exists(); Path('{tmp_path}/pnl.txt').write_text('0', encoding='utf-8')"
""",
    )

    steps = load_pipeline(pipeline)
    runner = RealizationDagRunner(steps)
    runner.run()

    assert (tmp_path / "pnl.txt").read_text(encoding="utf-8") == "0"
