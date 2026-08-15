"""Guard: the build package must not call the unused detector path."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
BUILD_PACKAGE = REPO_ROOT / "bengal" / "orchestration" / "build"

FORBIDDEN = ("find_work_early", "_detect_changes")


def test_build_package_does_not_reference_find_work_early() -> None:
    """Live invalidation is phase_incremental_filter_provenance, not find_work_early."""
    assert BUILD_PACKAGE.is_dir(), f"missing build package: {BUILD_PACKAGE}"

    hits: list[str] = []
    for path in sorted(BUILD_PACKAGE.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO_ROOT)
        hits.extend(f"{rel} references {name}" for name in FORBIDDEN if name in text)

    assert hits == [], (
        "bengal/orchestration/build/ must not reference find_work_early or "
        "_detect_changes; live invalidator is phase_incremental_filter_provenance.\n"
        + "\n".join(hits)
    )
