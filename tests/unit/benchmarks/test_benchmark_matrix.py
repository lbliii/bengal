"""Schema checks for the canonical benchmark matrix."""

from __future__ import annotations

import json
import shlex
import tomllib
from pathlib import Path

from benchmarks.run_matrix import (
    MatrixEntry,
    execute_entries,
    load_entries,
    write_receipt,
)

ROOT = Path(__file__).resolve().parents[3]
MATRIX_PATH = ROOT / "benchmarks" / "benchmark_matrix.toml"

REQUIRED_ENTRY_FIELDS = {
    "id",
    "tier",
    "tags",
    "purpose",
    "command",
    "paths",
    "metrics",
    "evidence",
    "budget",
    "triggers",
}
REQUIRED_TAGS = {
    "assets",
    "build",
    "cache",
    "incremental",
    "parser",
    "postprocess",
    "rendering",
    "worker-scaling",
}


def _load_matrix() -> dict:
    return tomllib.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def test_benchmark_matrix_entries_have_canonical_shape() -> None:
    matrix = _load_matrix()
    tiers = set(matrix["tiers"])
    entries = matrix["benchmarks"]

    assert matrix["version"] >= 1
    assert tiers == {"smoke", "release", "investigation"}
    assert entries

    seen_ids: set[str] = set()
    for entry in entries:
        missing_fields = REQUIRED_ENTRY_FIELDS.difference(entry)
        assert not missing_fields, f"{entry.get('id', '<missing>')} missing {missing_fields}"
        assert entry["id"] not in seen_ids
        assert entry["tier"] in tiers
        assert entry["command"].startswith("uv run ")
        assert entry["paths"]
        assert entry["tags"]
        assert entry["metrics"]
        assert entry["evidence"]

        seen_ids.add(entry["id"])


def test_benchmark_matrix_references_existing_sources() -> None:
    matrix = _load_matrix()

    for entry in matrix["benchmarks"]:
        for source_path in entry["paths"]:
            path = ROOT / source_path
            assert path.exists(), f"{entry['id']} references missing path: {source_path}"
            assert "/output/" not in source_path, (
                f"{entry['id']} must not depend on generated output"
            )
            assert source_path.startswith(("benchmarks/", "tests/performance/"))


def test_benchmark_matrix_commands_reference_tracked_paths() -> None:
    matrix = _load_matrix()

    for entry in matrix["benchmarks"]:
        tokens = shlex.split(entry["command"])
        command_paths = [
            token
            for token in tokens
            if token.startswith(("benchmarks/", "tests/performance/")) and "::" not in token
        ]
        assert command_paths, f"{entry['id']} command should name at least one benchmark path"
        for command_path in command_paths:
            assert (ROOT / command_path).exists(), (
                f"{entry['id']} command references missing path: {command_path}"
            )


def test_benchmark_matrix_covers_required_hot_paths() -> None:
    matrix = _load_matrix()
    covered_tags = {tag for entry in matrix["benchmarks"] for tag in entry["tags"]}

    assert REQUIRED_TAGS.issubset(covered_tags)


def test_matrix_runner_dry_run_returns_normalized_results() -> None:
    entry = MatrixEntry(
        id="render-output-regression",
        tier="smoke",
        command="uv run pytest tests/performance/test_autodoc_render_regression.py",
        purpose="Guard render output shape.",
    )

    exit_code, results = execute_entries([entry], dry_run=True)

    assert exit_code == 0
    assert len(results) == 1
    assert results[0].id == entry.id
    assert results[0].returncode == 0
    assert results[0].duration_seconds == 0.0
    assert results[0].skipped is True


def test_matrix_runner_writes_receipt(tmp_path: Path) -> None:
    entry = MatrixEntry(
        id="post-render-budget",
        tier="smoke",
        command="uv run pytest tests/performance/test_post_render_pipeline_budget.py",
        purpose="Guard post-render budget.",
    )
    exit_code, results = execute_entries([entry], dry_run=True)
    receipt_path = tmp_path / "matrix" / "receipt.json"

    write_receipt(
        receipt_path,
        entries=[entry],
        results=results,
        dry_run=True,
        exit_code=exit_code,
    )

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    assert receipt["version"] == 1
    assert receipt["dry_run"] is True
    assert receipt["exit_code"] == 0
    assert receipt["selected_ids"] == [entry.id]
    assert receipt["results"][0]["id"] == entry.id


def test_matrix_runner_loads_canonical_rows() -> None:
    entries = load_entries(MATRIX_PATH)

    assert entries
    assert {entry.tier for entry in entries} == {"smoke", "release", "investigation"}
