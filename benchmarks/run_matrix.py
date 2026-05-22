"""Run benchmark commands from the canonical benchmark matrix."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "benchmarks" / "benchmark_matrix.toml"
VALID_TIERS = ("smoke", "release", "investigation")


@dataclass(frozen=True, slots=True)
class MatrixEntry:
    """One executable benchmark matrix row."""

    id: str
    tier: str
    command: str
    purpose: str


def load_entries(matrix_path: Path = MATRIX_PATH) -> list[MatrixEntry]:
    """Load benchmark entries from a matrix TOML file."""
    matrix = tomllib.loads(matrix_path.read_text(encoding="utf-8"))
    return [
        MatrixEntry(
            id=entry["id"],
            tier=entry["tier"],
            command=entry["command"],
            purpose=entry["purpose"],
        )
        for entry in matrix["benchmarks"]
    ]


def select_entries(
    entries: list[MatrixEntry],
    *,
    tier: str | None = None,
    entry_ids: set[str] | None = None,
) -> list[MatrixEntry]:
    """Filter matrix entries by tier and/or id."""
    selected = entries
    if tier is not None:
        selected = [entry for entry in selected if entry.tier == tier]
    if entry_ids:
        selected = [entry for entry in selected if entry.id in entry_ids]
    return selected


def run_entries(entries: list[MatrixEntry], *, dry_run: bool = False) -> int:
    """Run selected benchmark entries in matrix order."""
    if not entries:
        print("No benchmark matrix entries selected.", file=sys.stderr)
        return 2

    for entry in entries:
        print(f"[{entry.tier}] {entry.id}")
        print(f"  {entry.command}")
        if dry_run:
            continue
        result = subprocess.run(entry.command, cwd=ROOT, shell=True, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=MATRIX_PATH, help="Path to benchmark matrix")
    parser.add_argument("--tier", choices=VALID_TIERS, help="Run one benchmark tier")
    parser.add_argument("--id", action="append", dest="ids", help="Run one matrix row id")
    parser.add_argument(
        "--list", action="store_true", help="List selected entries without commands"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print commands without executing them"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the benchmark matrix CLI."""
    args = build_parser().parse_args(argv)
    entries = select_entries(
        load_entries(args.matrix),
        tier=args.tier,
        entry_ids=set(args.ids or []),
    )

    if args.list:
        for entry in entries:
            print(f"{entry.tier:13} {entry.id:32} {entry.purpose}")
        return 0 if entries else 2

    return run_entries(entries, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
