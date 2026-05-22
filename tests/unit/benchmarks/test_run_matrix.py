"""Tests for the benchmark matrix runner."""

from __future__ import annotations

from typing import TYPE_CHECKING

from benchmarks import run_matrix

if TYPE_CHECKING:
    from pathlib import Path


def test_load_entries_reads_canonical_matrix() -> None:
    entries = run_matrix.load_entries()

    assert any(entry.id == "render-output-regression" for entry in entries)
    assert {entry.tier for entry in entries} == {"smoke", "release", "investigation"}


def test_select_entries_filters_by_tier_and_id() -> None:
    entries = [
        run_matrix.MatrixEntry("a", "smoke", "echo a", "A"),
        run_matrix.MatrixEntry("b", "release", "echo b", "B"),
        run_matrix.MatrixEntry("c", "smoke", "echo c", "C"),
    ]

    assert [entry.id for entry in run_matrix.select_entries(entries, tier="smoke")] == ["a", "c"]
    assert [
        entry.id for entry in run_matrix.select_entries(entries, tier="smoke", entry_ids={"c"})
    ] == ["c"]


def test_run_entries_dry_run_does_not_execute(monkeypatch) -> None:
    calls: list[str] = []

    def fake_run(*args, **kwargs):
        calls.append("called")
        raise AssertionError("dry run should not execute commands")

    monkeypatch.setattr(run_matrix.subprocess, "run", fake_run)

    exit_code = run_matrix.run_entries(
        [run_matrix.MatrixEntry("a", "smoke", "echo a", "A")],
        dry_run=True,
    )

    assert exit_code == 0
    assert calls == []


def test_run_entries_stops_on_failure(monkeypatch) -> None:
    commands: list[str] = []

    def fake_run(command: str, *, cwd: Path, shell: bool, check: bool):
        commands.append(command)
        return type("Result", (), {"returncode": 7})()

    monkeypatch.setattr(run_matrix.subprocess, "run", fake_run)

    exit_code = run_matrix.run_entries(
        [
            run_matrix.MatrixEntry("a", "smoke", "echo a", "A"),
            run_matrix.MatrixEntry("b", "smoke", "echo b", "B"),
        ]
    )

    assert exit_code == 7
    assert commands == ["echo a"]
