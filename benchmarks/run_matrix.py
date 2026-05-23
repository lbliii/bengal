"""Run benchmark commands from the canonical benchmark matrix."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter

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


@dataclass(frozen=True, slots=True)
class MatrixEntryResult:
    """Execution receipt for one benchmark matrix row."""

    id: str
    tier: str
    command: str
    returncode: int
    duration_seconds: float
    skipped: bool = False


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


def execute_entries(
    entries: list[MatrixEntry], *, dry_run: bool = False
) -> tuple[int, list[MatrixEntryResult]]:
    """Run selected benchmark entries in matrix order."""
    if not entries:
        print("No benchmark matrix entries selected.", file=sys.stderr)
        return 2, []

    results: list[MatrixEntryResult] = []
    for entry in entries:
        print(f"[{entry.tier}] {entry.id}")
        print(f"  {entry.command}")
        if dry_run:
            results.append(
                MatrixEntryResult(
                    id=entry.id,
                    tier=entry.tier,
                    command=entry.command,
                    returncode=0,
                    duration_seconds=0.0,
                    skipped=True,
                )
            )
            continue
        started = perf_counter()
        result = subprocess.run(entry.command, cwd=ROOT, shell=True, check=False)
        duration = perf_counter() - started
        results.append(
            MatrixEntryResult(
                id=entry.id,
                tier=entry.tier,
                command=entry.command,
                returncode=result.returncode,
                duration_seconds=round(duration, 6),
            )
        )
        if result.returncode != 0:
            return result.returncode, results
    return 0, results


def run_entries(entries: list[MatrixEntry], *, dry_run: bool = False) -> int:
    """Run selected benchmark entries in matrix order."""
    exit_code, _results = execute_entries(entries, dry_run=dry_run)
    return exit_code


def write_receipt(
    receipt_path: Path,
    *,
    entries: list[MatrixEntry],
    results: list[MatrixEntryResult],
    dry_run: bool,
    exit_code: int,
) -> None:
    """Write a normalized benchmark matrix execution receipt atomically."""
    payload = {
        "version": 1,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "dry_run": dry_run,
        "exit_code": exit_code,
        "selected_ids": [entry.id for entry in entries],
        "results": [
            {
                "id": result.id,
                "tier": result.tier,
                "command": result.command,
                "returncode": result.returncode,
                "duration_seconds": result.duration_seconds,
                "skipped": result.skipped,
            }
            for result in results
        ],
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=receipt_path.parent,
        prefix=f".{receipt_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        json.dump(payload, tmp, indent=2)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(receipt_path)


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
    parser.add_argument(
        "--receipt",
        type=Path,
        help="Write a normalized JSON receipt for the selected matrix run",
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

    exit_code, results = execute_entries(entries, dry_run=args.dry_run)
    if args.receipt is not None:
        write_receipt(
            args.receipt,
            entries=entries,
            results=results,
            dry_run=args.dry_run,
            exit_code=exit_code,
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
