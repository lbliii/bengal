"""Schema checks for the canonical benchmark matrix."""

from __future__ import annotations

import shlex
import tomllib
from pathlib import Path

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
