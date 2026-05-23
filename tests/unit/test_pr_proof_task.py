"""Guards for the bounded PR proof task."""

from __future__ import annotations

import tomllib
from pathlib import Path

from scripts.proof_pr_plan import proof_pr_plan

ROOT = Path(__file__).resolve().parents[2]


def _poe_tasks() -> dict:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return pyproject["tool"]["poe"]["tasks"]


def test_pr_proof_task_runs_checks_before_smoke_benchmarks() -> None:
    tasks = _poe_tasks()
    proof = tasks["proof-pr"]

    assert proof["sequence"] == [
        "lint",
        "format-check",
        "ty",
        "test-unit",
        "benchmark-smoke",
    ]


def test_benchmark_smoke_task_uses_canonical_fast_guards() -> None:
    task = _poe_tasks()["benchmark-smoke"]
    command = task["cmd"]

    assert "-o addopts= -n 0 -q" in command
    assert "tests/unit/benchmarks/test_benchmark_matrix.py" in command
    assert "tests/performance/test_autodoc_render_regression.py" in command
    assert "tests/performance/test_asset_fallback_cost.py" in command
    assert "tests/performance/test_post_render_pipeline_budget.py" in command


def test_proof_pr_plan_resolves_sequence_to_commands() -> None:
    plan = proof_pr_plan(ROOT)

    assert [step.name for step in plan] == [
        "lint",
        "format-check",
        "ty",
        "test-unit",
        "benchmark-smoke",
    ]
    assert all(step.command for step in plan)
    assert plan[-1].command == _poe_tasks()["benchmark-smoke"]["cmd"]
