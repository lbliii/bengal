"""
Unit tests for the incremental asset-manifest merge in ``_write_asset_manifest`` (#314).

These exercise the merge/carry-forward/prune logic directly, without a full build,
so they isolate the three behaviors independently of the asset-output-integrity
safety net (which, in an end-to-end build, would force a full reprocess and mask
the prune branch):

1. Incremental builds carry forward prior entries whose output still exists.
2. Prior entries whose output file is gone are pruned (the output-exists filter).
3. The reprocessed asset's entry is overlaid (current wins on a logical collision).
4. Full (non-incremental) builds ignore the prior manifest and rebuild from scratch.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from bengal.assets.manifest import AssetManifest
from bengal.core.asset import Asset
from bengal.core.site import Site
from bengal.orchestration.asset import AssetOrchestrator
from bengal.orchestration.build_state import BuildState

if TYPE_CHECKING:
    from pathlib import Path


def _site(tmp_path: Path) -> Site:
    root = tmp_path / "site"
    root.mkdir()
    (root / "bengal.toml").write_text('[site]\ntitle = "Merge Unit"\n')
    (root / "content").mkdir()
    (root / "content" / "index.md").write_text("---\ntitle: H\n---\n# H\n")
    return Site.from_config(root)


def _write_prior_manifest(output_dir: Path, entries: dict[str, str]) -> None:
    """Write a prior manifest mapping logical_path -> output_path (relative)."""
    manifest = AssetManifest()
    for logical, output in entries.items():
        manifest.set_entry(
            logical,
            output,
            fingerprint="old",
            size_bytes=3,
            updated_at=time.time(),
        )
    manifest.write(output_dir / "asset-manifest.json")


def _new_asset(output_dir: Path, logical: str, output_rel: str, tmp_path: Path) -> Asset:
    """A freshly-processed asset whose output file exists on disk."""
    out_file = output_dir / output_rel
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("new")
    src = tmp_path / "src" / logical
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("src")
    from pathlib import Path as _P

    return Asset(
        source_path=src,
        output_path=out_file,
        fingerprint="new",
        logical_path=_P(logical),
    )


def test_incremental_merge_carries_forward_prunes_and_overlays(tmp_path: Path) -> None:
    site = _site(tmp_path)
    out = site.output_dir
    out.mkdir(parents=True, exist_ok=True)
    site.set_build_state(BuildState(incremental=True))

    # Prior manifest: one entry whose output exists, one whose output is gone.
    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / "assets" / "keep.css").write_text("keep")
    _write_prior_manifest(
        out,
        {
            "css/keep.css": "assets/keep.css",  # output present -> carried forward
            "css/gone.css": "assets/gone.css",  # output absent -> pruned
        },
    )

    orch = AssetOrchestrator(site)
    new_asset = _new_asset(out, "js/new.js", "assets/new.js", tmp_path)
    orch._write_asset_manifest([new_asset])

    merged = AssetManifest.load(out / "asset-manifest.json")
    assert merged is not None
    entries = merged.entries
    assert "css/keep.css" in entries, "entry whose output exists must be carried forward"
    assert "css/gone.css" not in entries, "entry whose output is gone must be pruned"
    assert "js/new.js" in entries, "the reprocessed asset must be overlaid into the manifest"
    # Carried-forward entry keeps its prior metadata; overlaid entry is fresh.
    assert entries["css/keep.css"].fingerprint == "old"
    assert entries["js/new.js"].fingerprint == "new"


def test_incremental_overlay_wins_on_logical_collision(tmp_path: Path) -> None:
    """A reprocessed asset replaces its own prior entry (refreshed fingerprint)."""
    site = _site(tmp_path)
    out = site.output_dir
    out.mkdir(parents=True, exist_ok=True)
    site.set_build_state(BuildState(incremental=True))

    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / "assets" / "app.js").write_text("v1")
    _write_prior_manifest(out, {"js/app.js": "assets/app.js"})

    orch = AssetOrchestrator(site)
    reprocessed = _new_asset(out, "js/app.js", "assets/app.js", tmp_path)
    orch._write_asset_manifest([reprocessed])

    merged = AssetManifest.load(out / "asset-manifest.json")
    assert merged is not None
    assert merged.entries["js/app.js"].fingerprint == "new", (
        "the reprocessed asset's entry must win over the carried-forward prior entry"
    )


def test_full_build_rebuilds_from_scratch_ignoring_prior(tmp_path: Path) -> None:
    """Non-incremental builds do not carry forward prior entries."""
    site = _site(tmp_path)
    out = site.output_dir
    out.mkdir(parents=True, exist_ok=True)
    site.set_build_state(BuildState(incremental=False))

    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / "assets" / "keep.css").write_text("keep")
    _write_prior_manifest(out, {"css/keep.css": "assets/keep.css"})

    orch = AssetOrchestrator(site)
    new_asset = _new_asset(out, "js/new.js", "assets/new.js", tmp_path)
    orch._write_asset_manifest([new_asset])

    merged = AssetManifest.load(out / "asset-manifest.json")
    assert merged is not None
    assert set(merged.entries) == {"js/new.js"}, (
        "a full build rebuilds the manifest from only this run's assets, even though "
        "the prior entry's output still exists on disk"
    )
