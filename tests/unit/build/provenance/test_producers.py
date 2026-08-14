"""Unit tests for generated, track, and asset dependency-index producers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from bengal.build.contracts.keys import content_key
from bengal.build.provenance.filter import ProvenanceFilter
from bengal.build.provenance.lookups import (
    get_pages_for_asset,
    get_pages_for_generated,
    get_pages_for_track,
)
from bengal.build.provenance.producers import (
    add_asset_inputs,
    add_generated_inputs,
    add_track_inputs,
    generated_page_key,
)
from bengal.build.provenance.store import ProvenanceCache
from bengal.build.provenance.types import Provenance
from bengal.effects.effect import Effect
from bengal.effects.render_integration import BuildEffectTracer


def _page(
    source_path: Path,
    *,
    metadata: dict | None = None,
    virtual: bool = False,
    slug: str | None = None,
) -> MagicMock:
    page = MagicMock()
    page.source_path = source_path
    page.metadata = metadata or {}
    page.virtual = virtual
    page.template = None
    page._section = None
    page.slug = slug
    return page


def test_generated_page_key_from_taxonomy_metadata(tmp_path: Path) -> None:
    page = _page(
        tmp_path / ".bengal" / "generated" / "tags" / "python" / "index.md",
        metadata={"_generated": True, "_taxonomy_term": "python", "taxonomy": "tags"},
        virtual=True,
    )
    assert generated_page_key(page, tmp_path) == "tags/python"


def test_generated_page_key_skips_regular_content(tmp_path: Path) -> None:
    page = _page(tmp_path / "content" / "about.md", metadata={})
    assert generated_page_key(page, tmp_path) is None


def test_add_generated_inputs_emits_kind(tmp_path: Path) -> None:
    pf = SimpleNamespace(site=SimpleNamespace(root_path=tmp_path))
    page = _page(
        tmp_path / ".bengal" / "generated" / "tags" / "rust" / "index.md",
        metadata={"_generated": True, "tag": "rust"},
        virtual=True,
    )
    provenance = add_generated_inputs(pf, Provenance(), page)
    inputs = provenance.inputs_by_type("generated")
    assert [str(inp.path) for inp in inputs] == ["tags/rust"]


def test_add_track_inputs_from_track_page_and_items(tmp_path: Path) -> None:
    tracks = {
        "getting-started": {
            "title": "Getting Started",
            "items": ["guides/step1.md", "guides/step2.md"],
        }
    }
    pf = SimpleNamespace(
        site=SimpleNamespace(root_path=tmp_path, data=SimpleNamespace(tracks=tracks))
    )
    page = _page(
        tmp_path / "content" / "tracks" / "intro.md",
        metadata={"track_id": "getting-started", "template": "tracks/single.html"},
        slug="getting-started",
    )
    provenance = add_track_inputs(pf, Provenance(), page)
    keys = {str(inp.path) for inp in provenance.inputs_by_type("track")}
    assert keys == {"getting-started", "guides/step1.md", "guides/step2.md"}


def test_add_track_inputs_from_track_item_page(tmp_path: Path) -> None:
    tracks = {"getting-started": {"items": ["guides/step1.md"]}}
    pf = SimpleNamespace(
        site=SimpleNamespace(root_path=tmp_path, data=SimpleNamespace(tracks=tracks))
    )
    page = _page(tmp_path / "content" / "guides" / "step1.md", metadata={})
    provenance = add_track_inputs(pf, Provenance(), page)
    keys = {str(inp.path) for inp in provenance.inputs_by_type("track")}
    assert "getting-started" in keys
    assert "guides/step1.md" in keys


def test_add_asset_inputs_from_render_effects(tmp_path: Path) -> None:
    BuildEffectTracer.reset()
    tracer = BuildEffectTracer.activate()
    try:
        css = tmp_path / "assets" / "css" / "style.css"
        css.parent.mkdir(parents=True)
        css.write_text("body {}")
        page_path = tmp_path / "content" / "about.md"
        page_path.parent.mkdir(parents=True)
        page_path.write_text("# About")

        pf = SimpleNamespace(
            site=SimpleNamespace(root_path=tmp_path),
            _session_lock=__import__("threading").Lock(),
            _render_dependency_cache=None,
            _file_hashes={},
            _get_page_key=lambda page: content_key(page.source_path, tmp_path),
        )
        page = _page(page_path, metadata={})
        tracer.tracer.record(
            Effect(
                depends_on=frozenset({css}),
                operation="render_page",
                metadata={"source_path": str(page_path)},
            )
        )
        provenance = add_asset_inputs(pf, Provenance(), page)
        assert [str(inp.path) for inp in provenance.inputs_by_type("asset")] == [
            "assets/css/style.css"
        ]
    finally:
        BuildEffectTracer.reset()


def test_build_record_persists_generated_track_asset_index_entries(
    tmp_path: Path,
) -> None:
    """Producers land in the read-index with a producer field."""
    BuildEffectTracer.reset()
    tracer = BuildEffectTracer.activate()
    try:
        site_root = tmp_path / "site"
        css = site_root / "assets" / "css" / "style.css"
        css.parent.mkdir(parents=True)
        css.write_text("body {}")
        page_path = site_root / ".bengal" / "generated" / "tags" / "python" / "index.md"
        page_path.parent.mkdir(parents=True)
        page_path.write_text("# Python")

        site = MagicMock()
        site.root_path = site_root
        site.config = {"title": "Test"}
        site.data = SimpleNamespace(tracks={"getting-started": {"items": ["guides/step1.md"]}})

        cache = ProvenanceCache(cache_dir=tmp_path / "provenance")
        pf = ProvenanceFilter(site=site, cache=cache)

        page = _page(
            page_path,
            metadata={
                "_generated": True,
                "_taxonomy_term": "python",
                "taxonomy": "tags",
                "track_id": "getting-started",
            },
            virtual=True,
        )
        tracer.tracer.record(
            Effect(
                depends_on=frozenset({css}),
                operation="render_page",
                metadata={"source_path": str(page_path)},
            )
        )

        record_with_paths = pf.build_record(page)
        assert record_with_paths is not None
        record, _ = record_with_paths
        assert [str(inp.path) for inp in record.provenance.inputs_by_type("generated")] == [
            "tags/python"
        ]
        track_keys = {str(inp.path) for inp in record.provenance.inputs_by_type("track")}
        assert "getting-started" in track_keys
        assert [str(inp.path) for inp in record.provenance.inputs_by_type("asset")] == [
            "assets/css/style.css"
        ]

        cache.store(record)
        cache.save()
        index = cache.get_dependency_index()

        generated = index.get("generated", "tags/python")
        assert generated is not None
        assert generated.producer == "provenance"
        assert generated.invalidation_reason == "generated_dependency_changed"

        track = index.get("track", "getting-started")
        assert track is not None
        assert track.producer == "provenance"

        asset = index.get("asset", "assets/css/style.css")
        assert asset is not None
        assert asset.producer == "provenance"

        page_key = str(record.page_path)
        assert get_pages_for_generated(index, ("tags/python",)) == {Path(page_key)}
        assert get_pages_for_track(index, ("getting-started",)) == {Path(page_key)}

        class _Cache:
            def _cache_key(self, path: Path) -> str:
                return "assets/css/style.css"

        assert get_pages_for_asset(_Cache(), css, index) == {Path(page_key)}
    finally:
        BuildEffectTracer.reset()
