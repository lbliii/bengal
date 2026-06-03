"""
Regression tests for asset-manifest preservation on *partial* incremental builds.

GitHub Issue: #314 - Incremental asset manifest shrinks on partial asset rebuilds
(follow-on to #130).

#313 fixed the *content-only* case where ``AssetOrchestrator.process([])`` wiped
``asset-manifest.json`` to an empty manifest. But ``_write_asset_manifest`` still
rebuilt the manifest from **only the assets reprocessed this run**, so editing a
single asset (a *partial* incremental) rebuilt the manifest with just that one
entry and dropped every unchanged entry.

A shrunk manifest re-introduces the #130 failure class: ``inspect_asset_outputs``
reports a vacuously "complete" tree (few entries, all present, zero missing),
blinding the incremental reprocess safety net — a missing CSS/JS output then goes
unrecovered until a full rebuild.

The fix merges instead of rebuilding on incremental builds: prior entries whose
output file still exists are carried forward, then this run's freshly-processed
assets are overlaid. Full builds still rebuild from scratch (orphan-free).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

if TYPE_CHECKING:
    from pathlib import Path


def _manifest(output_dir: Path) -> dict[str, dict]:
    """Return the ``assets`` mapping of ``asset-manifest.json`` (empty if absent)."""
    manifest = output_dir / "asset-manifest.json"
    if not manifest.exists():
        return {}
    data = json.loads(manifest.read_text())
    return data.get("assets", {}) if isinstance(data, dict) else {}


class TestAssetManifestPartialIncrementalMerge:
    """Editing one asset must not drop the manifest's other entries (#314)."""

    @pytest.fixture
    def site_with_standalone_assets(self, tmp_path: Path) -> Path:
        """A default-theme site with several own *standalone* (non-bundled) assets.

        Standalone image assets are fingerprinted and copied individually, so
        editing one yields a true *partial* asset incremental (``process()`` runs
        on a single-asset subset) rather than a re-bundle or a forced full
        reprocess — which is exactly the path #314 regresses.
        """
        site_root = tmp_path / "site"
        site_root.mkdir()
        (site_root / "bengal.toml").write_text(
            """
[site]
title = "Asset Manifest Merge"

[build]
incremental = true

[assets]
fingerprint = true
minify = false
"""
        )
        content = site_root / "content"
        content.mkdir()
        (content / "index.md").write_text("---\ntitle: Home\n---\n\n# Home\n")

        img_dir = site_root / "assets" / "img"
        img_dir.mkdir(parents=True)
        for name in ("alpha", "beta", "gamma"):
            (img_dir / f"{name}.svg").write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" id="{name}"><rect/></svg>\n'
            )
        return site_root

    def test_partial_asset_incremental_preserves_full_manifest(
        self, site_with_standalone_assets: Path
    ) -> None:
        """Editing one asset keeps the manifest complete and refreshes only that entry."""
        site_root = site_with_standalone_assets
        alpha = site_root / "assets" / "img" / "alpha.svg"

        # Build 1: full build.
        site1 = Site.from_config(site_root)
        output_dir = site1.output_dir
        site1.build(BuildOptions(force_sequential=True, incremental=False))

        full = _manifest(output_dir)
        # Sanity: the three own assets plus theme assets are all recorded.
        assert {"img/alpha.svg", "img/beta.svg", "img/gamma.svg"} <= set(full), (
            "full build should record all standalone asset entries"
        )
        assert len(full) > 3, "full build should also record the theme's assets"
        alpha_fp_v1 = full["img/alpha.svg"]["fingerprint"]
        beta_entry_v1 = full["img/beta.svg"]

        # Edit ONLY alpha.svg -> a true partial asset incremental.
        alpha.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" id="alpha2"><rect width="9"/></svg>\n'
        )
        site2 = Site.from_config(site_root)
        site2.build(
            BuildOptions(
                force_sequential=True,
                incremental=True,
                changed_sources={alpha},
            )
        )

        partial = _manifest(output_dir)

        # Core #314 guard: the manifest must NOT shrink to just the reprocessed asset.
        assert len(partial) == len(full), (
            "partial asset incremental must preserve every manifest entry, not "
            f"shrink to the reprocessed subset (had {len(full)}, got {len(partial)}). "
            "A shrunk manifest re-introduces the #130 vacuous-complete blindness."
        )

        # Unchanged asset entry is carried forward verbatim.
        assert partial.get("img/beta.svg") == beta_entry_v1, (
            "an unchanged asset's manifest entry must be carried forward unchanged"
        )

        # Edited asset entry is refreshed (new fingerprint, output present).
        assert "img/alpha.svg" in partial, "edited asset must remain in the manifest"
        alpha_fp_v2 = partial["img/alpha.svg"]["fingerprint"]
        assert alpha_fp_v2 != alpha_fp_v1, (
            "edited asset's manifest entry must be refreshed with its new fingerprint"
        )
        assert (output_dir / partial["img/alpha.svg"]["output_path"]).exists(), (
            "edited asset's new fingerprinted output must exist on disk"
        )

    def test_full_rebuild_after_incremental_is_orphan_free(
        self, site_with_standalone_assets: Path
    ) -> None:
        """A full rebuild rebuilds from scratch — same entry set as the first full build.

        Guards that the incremental merge does not leak orphan entries into the
        full-build path (the merge is gated to incremental builds only).
        """
        site_root = site_with_standalone_assets
        alpha = site_root / "assets" / "img" / "alpha.svg"

        site1 = Site.from_config(site_root)
        output_dir = site1.output_dir
        site1.build(BuildOptions(force_sequential=True, incremental=False))
        full_v1 = set(_manifest(output_dir))

        # Partial incremental (merges/carries forward).
        alpha.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" id="a2"><rect width="3"/></svg>\n'
        )
        site2 = Site.from_config(site_root)
        site2.build(BuildOptions(force_sequential=True, incremental=True, changed_sources={alpha}))

        # A subsequent full build rebuilds from scratch.
        site3 = Site.from_config(site_root)
        site3.build(BuildOptions(force_sequential=True, incremental=False))
        full_v2 = set(_manifest(output_dir))

        assert full_v2 == full_v1, (
            "full rebuild after an incremental must yield the same manifest entry set "
            "(the merge is incremental-only and must not leak orphans into full builds)"
        )
