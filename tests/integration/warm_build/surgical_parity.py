"""
Byte-parity harness for the persistent-resident-Site warm-rebuild work (#522).

The persistent-site model (``plan/rfc-persistent-resident-site.md``) only ships a
change-type once a surgical warm rebuild is *proven byte-identical* to a full
cold rebuild of the same final state. This module is that proof harness — a
reusable, discriminating output-tree comparison plus the determinism floor it
rests on.

Steward contract (``bengal/orchestration/incremental/AGENTS.md``): "warm equals
cold". A green parity test only means something if its comparison would FAIL when
the surgical path under-rebuilds — hence the discriminating-power guard test
(#130 vacuous-test lesson).

Phase 0 uses this to lock in the determinism floor (two full builds of the same
source are byte-identical after normalizing known nondeterminism) and the
discriminating power of the comparison. Later phases call
:func:`assert_surgical_matches_full` to gate each enabled change-type.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

if TYPE_CHECKING:
    from collections.abc import Callable

    from bengal.orchestration.incremental.state_mutator import SiteStateMutator

# Known build-output nondeterminism: ISO-8601 timestamps embedded in JSON
# sidecars / text artifacts (index.json, agent.json, llm-full.txt headers). These
# are the documented exception to byte-determinism, so the parity comparison
# normalizes them rather than flagging them as real divergence.
_ISO_TS = re.compile(rb"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?")
_TS_PLACEHOLDER = b"<TS>"

# Text-ish output extensions we normalize timestamps in. Binary outputs (images,
# fonts) are compared byte-for-byte with no normalization.
_TEXT_SUFFIXES = {".html", ".json", ".xml", ".txt", ".md", ".css", ".js", ".rss", ".atom"}

# Derived integrity-hash sidecars (e.g. ``index.json.hash``) are sha256 of the
# *raw* artifact, which legitimately includes the build timestamp we normalize
# away — so the hash varies even when the content is byte-identical. They are a
# separate stale-output integrity net (#130/#314), not page content, so the
# parity comparison (which already diffs the content directly, normalized)
# excludes them rather than flagging the propagated timestamp noise.
_SKIP_SUFFIXES = {".hash"}


def normalize_bytes(rel_path: str, content: bytes) -> bytes:
    """Normalize documented nondeterminism (timestamps) for text-ish outputs."""
    suffix = Path(rel_path).suffix.lower()
    if suffix in _TEXT_SUFFIXES:
        return _ISO_TS.sub(_TS_PLACEHOLDER, content)
    return content


def snapshot_output_tree(output_dir: Path, *, normalize: bool = True) -> dict[str, bytes]:
    """Map every output file (relative posix path) to its (normalized) bytes."""
    snapshot: dict[str, bytes] = {}
    if not output_dir.exists():
        return snapshot
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in _SKIP_SUFFIXES:
            continue
        rel = path.relative_to(output_dir).as_posix()
        data = path.read_bytes()
        snapshot[rel] = normalize_bytes(rel, data) if normalize else data
    return snapshot


def diff_trees(a: dict[str, bytes], b: dict[str, bytes]) -> list[str]:
    """Return human-readable diffs between two output snapshots (empty == equal)."""
    diffs: list[str] = []
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    diffs.extend(f"only in A: {p}" for p in only_a)
    diffs.extend(f"only in B: {p}" for p in only_b)
    diffs.extend(
        f"differs: {p} ({len(a[p])}B vs {len(b[p])}B)"
        for p in sorted(set(a) & set(b))
        if a[p] != b[p]
    )
    return diffs


def assert_trees_equal(a: dict[str, bytes], b: dict[str, bytes], *, context: str) -> None:
    """Assert two output snapshots are byte-identical (after normalization)."""
    diffs = diff_trees(a, b)
    assert not diffs, f"output-tree parity FAILED ({context}):\n  " + "\n  ".join(diffs[:40])


def _reset_process_build_globals() -> None:
    """Reset module/thread-global build state so each build is hermetic.

    The dev server resets these between warm builds (``reset_ephemeral_state``);
    two raw full builds in one test process would otherwise share accumulating
    process globals (the asset manifest, created-dirs set), making two builds of
    identical source differ — a comparison artifact, not real nondeterminism.
    Mirroring the reset keeps the parity comparison apples-to-apples.
    """
    from bengal.rendering.assets import reset_asset_manifest
    from bengal.rendering.pipeline.thread_local import get_created_dirs

    get_created_dirs().clear()
    reset_asset_manifest()


def _cold_build(site_dir: Path) -> Path:
    """Run a full (cold) build of ``site_dir`` and return its output dir."""
    _reset_process_build_globals()
    site = Site.from_config(site_dir)
    site.discover_content()
    site.discover_assets()
    site.build(BuildOptions(incremental=False, force_sequential=True))
    return site_dir / "public"


def _copy_site(src: Path, dst: Path) -> Path:
    """Copy a site tree to ``dst`` excluding build/cache artifacts."""
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns("public", ".bengal", "__pycache__"),
    )
    return dst


def assert_full_build_deterministic(site_dir: Path, work_dir: Path) -> None:
    """Two independent full builds of the same source are byte-identical.

    This is the floor the surgical parity gate rests on: if a clean rebuild is
    not reproducible, no incremental==full claim can be trusted. Builds happen in
    two fresh copies (independent ``.bengal`` caches) under ``work_dir``.
    """
    a = _cold_build(_copy_site(site_dir, work_dir / "det_a"))
    b = _cold_build(_copy_site(site_dir, work_dir / "det_b"))
    assert_trees_equal(
        snapshot_output_tree(a),
        snapshot_output_tree(b),
        context="two full builds of identical source",
    )


def assert_surgical_matches_full(
    site_dir: Path,
    work_dir: Path,
    apply_change: Callable[[Path], None],
    surgical_rebuild: Callable[[Path], SiteStateMutator | None],
) -> None:
    """Gate a change-type: surgical warm rebuild must equal a full rebuild.

    Both legs start from a cold build of ``site_dir`` in a fresh copy, then apply
    the SAME ``apply_change`` to reach the same final state:

    * leg A runs ``surgical_rebuild`` (the resident-Site mutation path);
    * leg B runs a full cold rebuild.

    Their output trees must be byte-identical (after normalization). Until a
    change-type is enabled, ``surgical_rebuild`` falls back to a full rebuild, so
    this asserts the harness + fallback wiring, not yet a real surgical win.
    """
    a_dir = _copy_site(site_dir, work_dir / "surgical")
    _cold_build(a_dir)
    apply_change(a_dir)
    # The dev server resets process-global build state before every rebuild;
    # mirror that so the surgical leg starts as hermetically as the full leg.
    _reset_process_build_globals()
    surgical_rebuild(a_dir)  # leg A: surgical (or fallback to full)
    a = snapshot_output_tree(a_dir / "public")

    b_dir = _copy_site(site_dir, work_dir / "full")
    _cold_build(b_dir)
    apply_change(b_dir)
    _cold_build(b_dir)  # leg B: full rebuild of the final state
    b = snapshot_output_tree(b_dir / "public")

    assert_trees_equal(a, b, context="surgical warm rebuild vs full rebuild")
