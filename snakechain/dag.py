from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, List, Optional

import yaml


class DagConfigError(Exception):
    """Raised when the DAG configuration is invalid."""


class DagExecutionError(Exception):
    """Raised when a DAG step fails during execution."""


class StepType(str, Enum):
    FETCH_DATA = "fetch_data"
    HUMAN_GATE = "human_gate"
    SIGNAL_GENERATOR = "signal_generator"
    PROFIT_EVALUATOR = "profit_evaluator"


@dataclass
class DagStep:
    name: str
    type: StepType
    command: str
    proof_path: Optional[Path] = None
    expected_token: Optional[str] = None

    def requires_proof(self) -> bool:
        return self.type == StepType.HUMAN_GATE


def _load_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:  # pragma: no cover - YAML errors should be rare
        raise DagConfigError(f"Invalid YAML: {exc}") from exc


def load_pipeline(path: Path) -> List[DagStep]:
    data = _load_yaml(path)
    if not isinstance(data, dict) or "steps" not in data:
        raise DagConfigError("Pipeline file must be a mapping containing 'steps'")

    steps: List[DagStep] = []
    for raw in data.get("steps", []):
        if not {"name", "type", "command"}.issubset(raw):
            raise DagConfigError("Each step requires name, type, and command")
        step_type = StepType(raw["type"])
        proof_path = Path(raw["proof_path"]) if "proof_path" in raw else None
        steps.append(
            DagStep(
                name=raw["name"],
                type=step_type,
                command=raw["command"],
                proof_path=proof_path,
                expected_token=raw.get("expected_token"),
            )
        )
    _validate_step_sequence(steps)
    return steps


def _validate_step_sequence(steps: Iterable[DagStep]) -> None:
    sequence = [step.type for step in steps]
    required_order = [
        StepType.FETCH_DATA,
        StepType.HUMAN_GATE,
        StepType.SIGNAL_GENERATOR,
        StepType.PROFIT_EVALUATOR,
    ]
    if sequence[: len(required_order)] != required_order:
        raise DagConfigError("Pipeline must start with fetch_data → human_gate → signal_generator → profit_evaluator")


class RealizationDagRunner:
    """Execute a Realization-Only DAG with enforced human proof points."""

    def __init__(
        self,
        steps: List[DagStep],
        *,
        block_for_proof: bool = False,
        poll_interval: float = 2.0,
        proof_timeout: Optional[float] = None,
    ) -> None:
        self.steps = steps
        self.block_for_proof = block_for_proof
        self.poll_interval = poll_interval
        self.proof_timeout = proof_timeout

    def run(self) -> None:
        for step in self.steps:
            if step.requires_proof():
                self._assert_proof(step)
            self._run_command(step)

    def _assert_proof(self, step: DagStep) -> None:
        if not step.proof_path:
            raise DagConfigError("human_gate steps require a proof_path")

        start = time.monotonic()
        while True:
            if self._proof_satisfied(step):
                return
            if not self.block_for_proof:
                raise DagExecutionError(f"Proof not present for {step.name}: {step.proof_path}")
            if self.proof_timeout is not None and (time.monotonic() - start) > self.proof_timeout:
                raise DagExecutionError(f"Timed out waiting for proof at {step.proof_path}")
            time.sleep(self.poll_interval)

    def _proof_satisfied(self, step: DagStep) -> bool:
        assert step.proof_path is not None
        if not step.proof_path.exists():
            return False
        if step.expected_token:
            content = step.proof_path.read_text(encoding="utf-8")
            return step.expected_token in content
        return True

    def _run_command(self, step: DagStep) -> None:
        result = subprocess.run(
            step.command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise DagExecutionError(
                f"Step '{step.name}' failed with code {result.returncode}: {result.stderr.strip()}"
            )

