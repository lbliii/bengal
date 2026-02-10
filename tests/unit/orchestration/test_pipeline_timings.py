"""Tests for persisted pipeline timing hints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from bengal.orchestration.pipeline import execute_pipeline
from bengal.orchestration.pipeline.task import BuildTask
from bengal.orchestration.pipeline.timings import load_task_timings, update_task_timings


def test_load_task_timings_missing_file_returns_empty(tmp_path: Path) -> None:
    """Missing timing file should return an empty mapping."""
    assert load_task_timings(tmp_path) == {}


def test_update_task_timings_persists_and_merges(tmp_path: Path) -> None:
    """update_task_timings should persist EWMA-merged values."""
    update_task_timings(tmp_path, {"parse_content": 100.0, "render_pages": 200.0})
    initial = load_task_timings(tmp_path)
    assert initial["parse_content"] == 100.0
    assert initial["render_pages"] == 200.0

    # EWMA alpha=0.35 -> new value moves toward observed.
    update_task_timings(tmp_path, {"parse_content": 300.0})
    merged = load_task_timings(tmp_path)
    assert merged["parse_content"] > 100.0
    assert merged["parse_content"] < 300.0


def test_load_supports_only_valid_positive_numeric_entries(tmp_path: Path) -> None:
    """Invalid timing entries should be ignored at load time."""
    path = tmp_path / ".bengal" / "state" / "pipeline_task_timings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "valid": 12.5,
                "zero": 0.0,
                "negative": -1.0,
                "bad_type": "fast",
                    "1": 2.0,
            }
        )
    )

    timings = load_task_timings(tmp_path)
    assert timings == {"valid": 12.5, "1": 2.0}


def test_execute_pipeline_persists_completed_task_timings(tmp_path: Path) -> None:
    """execute_pipeline should persist timing hints when site root is available."""

    @dataclass
    class _Site:
        root_path: Path

    @dataclass
    class _Ctx:
        site: _Site

    def _run(_ctx: _Ctx) -> None:
        return

    tasks = [
        BuildTask(
            name="a",
            requires=frozenset(),
            produces=frozenset({"a_out"}),
            execute=_run,
        ),
        BuildTask(
            name="b",
            requires=frozenset({"a_out"}),
            produces=frozenset({"b_out"}),
            execute=_run,
        ),
    ]

    result = execute_pipeline(
        tasks=tasks,
        ctx=_Ctx(site=_Site(root_path=tmp_path)),
        initial_keys=frozenset(),
        parallel=False,
    )

    assert result.success
    timings = load_task_timings(tmp_path)
    assert "a" in timings
    assert "b" in timings


def test_execute_pipeline_skips_timing_hints_when_disabled(tmp_path: Path) -> None:
    """execute_pipeline should not persist timing hints when disabled."""

    @dataclass
    class _Site:
        root_path: Path

    @dataclass
    class _Ctx:
        site: _Site

    def _run(_ctx: _Ctx) -> None:
        return

    tasks = [
        BuildTask(
            name="single",
            requires=frozenset(),
            produces=frozenset({"single_out"}),
            execute=_run,
        )
    ]

    result = execute_pipeline(
        tasks=tasks,
        ctx=_Ctx(site=_Site(root_path=tmp_path)),
        initial_keys=frozenset(),
        parallel=False,
        use_timing_hints=False,
    )

    assert result.success
    assert load_task_timings(tmp_path) == {}
