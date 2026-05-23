"""Print the canonical bounded PR proof plan."""

from __future__ import annotations

import argparse
import json
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class ProofPlanStep:
    """One resolved task in the bounded PR proof path."""

    name: str
    command: str
    help: str


def _load_poe_tasks(root: Path) -> dict[str, Any]:
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return pyproject["tool"]["poe"]["tasks"]


def _task_sequence(task: Any, *, task_name: str) -> tuple[str, ...]:
    if not isinstance(task, dict):
        raise TypeError(f"{task_name} must be a table in [tool.poe.tasks]")
    sequence = task.get("sequence")
    if not isinstance(sequence, list) or not all(isinstance(item, str) for item in sequence):
        raise TypeError(f"{task_name} must define a string sequence")
    return tuple(sequence)


def _task_command(task: Any, *, task_name: str) -> str:
    if not isinstance(task, dict):
        raise TypeError(f"{task_name} must be a table in [tool.poe.tasks]")
    command = task.get("cmd")
    if not isinstance(command, str) or not command:
        raise TypeError(f"{task_name} must define a non-empty cmd")
    return command


def _task_help(task: Any, *, task_name: str) -> str:
    if not isinstance(task, dict):
        raise TypeError(f"{task_name} must be a table in [tool.poe.tasks]")
    help_text = task.get("help", "")
    if not isinstance(help_text, str):
        raise TypeError(f"{task_name} help must be a string")
    return help_text


def proof_pr_plan(root: Path = ROOT) -> tuple[ProofPlanStep, ...]:
    """Return the resolved bounded PR proof plan from pyproject tasks."""
    tasks = _load_poe_tasks(root)
    sequence = _task_sequence(tasks["proof-pr"], task_name="proof-pr")
    return tuple(
        ProofPlanStep(
            name=task_name,
            command=_task_command(tasks[task_name], task_name=task_name),
            help=_task_help(tasks[task_name], task_name=task_name),
        )
        for task_name in sequence
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    plan = proof_pr_plan()
    if args.format == "json":
        print(json.dumps([asdict(step) for step in plan], indent=2))
        return 0

    for index, step in enumerate(plan, start=1):
        print(f"{index}. {step.name}: {step.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
