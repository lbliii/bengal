"""Build-output snapshot regression harness.

Purpose
-------
Track B of the Errors & Site S-Tier epic (plan/immutable-floating-sun.md)
refactors `bengal.core.site.Site` without changing build output. This test
locks that invariant: for a known-good test root, every file's SHA256
must match a committed manifest. Any content drift fails the build.

Usage
-----
Skipped by default. Two opt-in modes via env var:

    BENGAL_SNAPSHOT=record   Build the test root and write the manifest.
                             Run once on a clean main-branch checkout BEFORE
                             starting a refactor sprint. Commit the manifest.

    BENGAL_SNAPSHOT=verify   Build the test root and assert every file's
                             SHA256 matches the manifest. Run at every sprint
                             boundary during Track B refactor.

Failure mode is verbose: lists every file that differs (added, removed,
changed), with the first N bytes of diff context for text files.

Targeted root is `test-basic` — covers the common build path without
pulling in heavyweight extras (autodoc, i18n) whose output is acceptable
to let drift during refactor.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

import pytest

SNAPSHOT_MODE = os.environ.get("BENGAL_SNAPSHOT", "").lower()
SNAPSHOT_ENABLED = SNAPSHOT_MODE in {"record", "verify"}

MANIFEST_PATH = Path(__file__).parent / "_snapshots" / "build_snapshot_test_basic.json"

# Files whose content is acceptably non-deterministic across environments
# (timestamps, build IDs, etc.). Listed as glob patterns relative to output_dir.
# Keep this list minimal — prefer deterministic output.
VOLATILE_PATTERNS: tuple[str, ...] = (
    # Build metadata with embedded timestamps or non-deterministic ordering
    "index.json",
    "index.json.hash",
    "sitemap.xml",
    "agent.json",
    "changelog.json",
    "asset-manifest.json",
    ".well-known/content-signals.json",
    # Autodoc & cache artifacts (not produced by test-basic, listed for safety)
    "**/.bengal-cache/**",
    # Graph JSON — embeds build-time IDs; excluded from snapshot
    "graph.json",
    "graph/*.json",
)


@dataclass(frozen=True, slots=True)
class FileEntry:
    path: str  # relative to output_dir
    size: int
    sha256: str


def _iter_output_files(output_dir: Path) -> list[Path]:
    """Return sorted list of files under output_dir, relative ordering."""
    return sorted(p for p in output_dir.rglob("*") if p.is_file())


def _is_volatile(rel_path: str) -> bool:
    from fnmatch import fnmatch

    return any(fnmatch(rel_path, pat) for pat in VOLATILE_PATTERNS)


def _hash_file(path: Path) -> tuple[int, str]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
            size += len(chunk)
    return size, h.hexdigest()


def _build_manifest(output_dir: Path) -> dict[str, FileEntry]:
    entries: dict[str, FileEntry] = {}
    for path in _iter_output_files(output_dir):
        rel = str(path.relative_to(output_dir))
        if _is_volatile(rel):
            continue
        size, digest = _hash_file(path)
        entries[rel] = FileEntry(path=rel, size=size, sha256=digest)
    return entries


def _write_manifest(manifest: dict[str, FileEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {k: {"size": v.size, "sha256": v.sha256} for k, v in sorted(manifest.items())}
    path.write_text(json.dumps(serializable, indent=2, sort_keys=True) + "\n")


def _load_manifest(path: Path) -> dict[str, FileEntry]:
    raw = json.loads(path.read_text())
    return {k: FileEntry(path=k, size=v["size"], sha256=v["sha256"]) for k, v in raw.items()}


def _diff_manifests(
    expected: dict[str, FileEntry],
    actual: dict[str, FileEntry],
) -> tuple[list[str], list[str], list[tuple[str, FileEntry, FileEntry]]]:
    expected_keys = set(expected)
    actual_keys = set(actual)
    added = sorted(actual_keys - expected_keys)
    removed = sorted(expected_keys - actual_keys)
    changed = [
        (k, expected[k], actual[k])
        for k in sorted(expected_keys & actual_keys)
        if expected[k].sha256 != actual[k].sha256
    ]
    return added, removed, changed


@pytest.mark.skipif(
    not SNAPSHOT_ENABLED,
    reason="Set BENGAL_SNAPSHOT=record or BENGAL_SNAPSHOT=verify to enable",
)
@pytest.mark.bengal(testroot="test-basic")
def test_build_output_snapshot(site, build_site):
    """
    Build test-basic and compare output against committed manifest.

    See module docstring for record/verify modes.
    """
    build_site()
    manifest = _build_manifest(site.output_dir)

    if SNAPSHOT_MODE == "record":
        _write_manifest(manifest, MANIFEST_PATH)
        pytest.skip(f"Recorded {len(manifest)} entries to {MANIFEST_PATH}")

    # verify mode
    if not MANIFEST_PATH.exists():
        pytest.fail(
            f"No snapshot found at {MANIFEST_PATH}. "
            f"Run `BENGAL_SNAPSHOT=record pytest {__file__}` from a clean main-branch checkout first."
        )

    expected = _load_manifest(MANIFEST_PATH)
    added, removed, changed = _diff_manifests(expected, manifest)

    if added or removed or changed:
        parts: list[str] = [
            f"Build output diverged from snapshot at {MANIFEST_PATH}",
            "",
        ]
        if removed:
            parts.append(f"MISSING ({len(removed)}):")
            parts.extend(f"  - {p}" for p in removed[:20])
            if len(removed) > 20:
                parts.append(f"  ... +{len(removed) - 20} more")
            parts.append("")
        if added:
            parts.append(f"UNEXPECTED ({len(added)}):")
            parts.extend(f"  + {p}" for p in added[:20])
            if len(added) > 20:
                parts.append(f"  ... +{len(added) - 20} more")
            parts.append("")
        if changed:
            parts.append(f"CHANGED ({len(changed)}):")
            for rel, exp, act in changed[:20]:
                parts.append(f"  ~ {rel}")
                parts.append(f"      expected: {exp.sha256[:16]} ({exp.size}B)")
                parts.append(f"      actual:   {act.sha256[:16]} ({act.size}B)")
            if len(changed) > 20:
                parts.append(f"  ... +{len(changed) - 20} more")
        pytest.fail("\n".join(parts))
