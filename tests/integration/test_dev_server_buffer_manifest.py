"""
Dev-server-realistic regression test for asset-manifest buffer divergence.

GitHub Issue: #315 - Dev-server hot-reload: asset-manifest can diverge between
double-buffers under delta-staging (residual #130).

The dev server double-buffers output: the ASGI app serves from the *active*
buffer while the next build writes to a *staging* buffer, then swaps. To avoid
re-seeding the whole tree each rebuild, ``BufferManager.prepare_delta_staging``
seeds staging from active using only the *previous* build's changed outputs.

But ``asset-manifest.json`` is special: its content describes the *currently
served buffer*, and a content-only rebuild never rewrites it — so it never lands
in the changed-output delta. Without an explicit sync it drifts a generation
behind across alternating swaps. When a buffer then becomes active carrying a
stale manifest, it can be missing entries for assets the buffer actually holds
(``asset_url`` fails to resolve them) and ``inspect_asset_outputs`` mis-reports
completeness — the residual mechanism behind #130's intermittent "unstyled,
fixed by restart" symptom that the build-API fix (#313) did not cover.

There was previously no realistic test for the dev-server buffer/swap/delta
path (the #130 tests use the build API, not ``BufferManager``). This harness
drives ``BufferManager.for_dev_server`` + ``prepare_staging`` /
``prepare_delta_staging`` + warm incremental rebuilds + ``swap()`` over many
cycles, mirroring ``DevServerBuildTrigger``'s real flow, and asserts that after
every swap the active buffer's manifest stays consistent with the active
buffer's files.

Verified to fail before the fix (``always_sync`` omitted): an asset added
mid-session goes missing from the manifest after content-only swaps that land on
the buffer that never processed the add.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.server.buffer_manager import BufferManager

if TYPE_CHECKING:
    from collections.abc import Iterable

# Mirror DevServerBuildTrigger: asset-manifest.json is synced from active on
# every delta-staging so a swapped-in buffer never serves a stale manifest.
_ALWAYS_SYNC = ("asset-manifest.json",)


def _buffer_delta_paths(
    changed_outputs: Iterable[object], active_root: Path
) -> tuple[Path, ...] | None:
    """Normalize an OutputCollector's records to relative output paths.

    Faithfully mirrors ``DevServerBuildTrigger._buffer_delta_paths`` — including its
    error semantics: an unresolvable or escaping path returns ``None`` (not a
    partial tuple), which signals ``prepare_delta_staging`` to fall back to a full
    seed. Matching this is what lets the harness exercise the real fallback path
    rather than masking it.
    """
    paths: list[Path] = []
    seen: set[Path] = set()
    for rec in changed_outputs:
        raw = Path(str(getattr(rec, "path", "")))
        if raw == Path("."):
            continue
        if raw.is_absolute():
            try:
                raw = raw.resolve().relative_to(active_root.resolve())
            except OSError, ValueError:
                return None
        if any(part == ".." for part in raw.parts):
            return None
        if raw not in seen:
            seen.add(raw)
            paths.append(raw)
    return tuple(paths)


def _active_manifest_assets(active_dir: Path) -> dict[str, dict]:
    manifest = active_dir / "asset-manifest.json"
    if not manifest.exists():
        return {}
    data = json.loads(manifest.read_text())
    return data.get("assets", {}) if isinstance(data, dict) else {}


class TestDevServerBufferManifest:
    """The active buffer must never serve a stale/divergent asset manifest (#315)."""

    @pytest.fixture
    def site_root(self, tmp_path: Path) -> Path:
        """A site with its own JS asset, configured like the dev server (no fingerprint)."""
        root = tmp_path / "site"
        root.mkdir()
        # fingerprint disabled mirrors the dev server (_prepare_dev_config), which
        # serves stable filenames for hot reload.
        (root / "bengal.toml").write_text(
            """
[site]
title = "Dev Buffer Manifest"

[build]
incremental = true

[assets]
fingerprint = false
minify = false
"""
        )
        content = root / "content"
        content.mkdir()
        (content / "index.md").write_text("---\ntitle: Home\n---\n\n# Home\n")
        js_dir = root / "assets" / "js"
        js_dir.mkdir(parents=True)
        (js_dir / "app.js").write_text("console.log('app');\n")
        return root

    def test_manifest_stays_consistent_across_buffer_swaps(self, site_root: Path) -> None:
        """Across many content + asset rebuilds, the active manifest tracks the buffer.

        Adding an asset mid-session and then making content-only edits forces the
        swaps to alternate buffers, one of which never processed the asset add.
        Without the manifest sync, that buffer becomes active carrying a manifest
        that omits the added asset; with the sync, every swap leaves a manifest
        that lists every site asset and points only to files present in the buffer.
        """
        content = site_root / "content" / "index.md"
        extra_js = site_root / "assets" / "js" / "extra.js"

        staging_dir = site_root / ".bengal" / "staging"
        out_dir = site_root / "public"
        mgr = BufferManager.for_dev_server(output_dir=out_dir, staging_dir=staging_dir)
        mgr.setup()

        site = Site.from_config(site_root)
        site.dev_mode = True

        # Initial full build writes to the active buffer (dev-server startup).
        site.output_dir = mgr.active_dir
        site.build(BuildOptions(force_sequential=True, incremental=False))

        expected_assets = {"js/app.js"}
        last_delta: tuple[Path, ...] | None = None

        def rebuild(changed: list[Path]) -> None:
            nonlocal last_delta
            if last_delta is not None:
                staging = mgr.prepare_delta_staging(last_delta, always_sync=_ALWAYS_SYNC)
            else:
                staging = mgr.prepare_staging()
            site.output_dir = staging
            stats = site.build(
                BuildOptions(
                    force_sequential=True,
                    incremental=True,
                    changed_sources=set(changed),
                )
            )
            mgr.swap()
            site.output_dir = mgr.active_dir
            last_delta = _buffer_delta_paths(getattr(stats, "changed_outputs", []), mgr.active_dir)

            assets = _active_manifest_assets(mgr.active_dir)
            # The active buffer's manifest must list every current site asset...
            missing = expected_assets - set(assets)
            assert not missing, (
                f"gen {mgr.generation}: active buffer serving a divergent manifest "
                f"missing {sorted(missing)} (asset_url would fail to resolve them and "
                "the output-integrity check would mis-report completeness — #315)"
            )
            # ...and every entry must point to a file present in the active buffer.
            for logical, entry in assets.items():
                output = mgr.active_dir / entry["output_path"]
                assert output.exists(), (
                    f"gen {mgr.generation}: manifest entry {logical!r} points to "
                    f"{entry['output_path']} which is missing from the active buffer"
                )

        steps: list[tuple[str, Path, str]] = [
            ("content", content, "# edit 1"),
            ("content", content, "# edit 2"),
            ("add", extra_js, "console.log('extra');\n"),
            ("content", content, "# edit 3"),
            ("content", content, "# edit 4"),
            ("content", content, "# edit 5"),
        ]
        for kind, target, body in steps:
            if kind == "add":
                target.write_text(body)
                expected_assets.add("js/extra.js")
                rebuild([target])
            else:
                target.write_text(f"---\ntitle: Home\n---\n\n{body}\n")
                rebuild([target])
