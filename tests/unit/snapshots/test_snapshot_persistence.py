"""
Tests for snapshot persistence type coercion.

Ensures reading_time, word_count, excerpt from cache/JSON round-trip
remain usable in comparisons and template rendering (no int/str TypeError).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from bengal.snapshots.persistence import (
    SNAPSHOT_VERSION,
    CachedPageData,
    SnapshotCache,
    apply_cached_parsing,
)
from bengal.snapshots.utils import compute_content_hash

# =============================================================================
# CachedPageData load from dirty JSON
# =============================================================================


class TestSnapshotCacheLoadFromDirtyJson:
    """Verify load_page_cache coerces string values to int."""

    def test_reading_time_word_count_coerced_from_strings(self, tmp_path: Path) -> None:
        """JSON with string reading_time/word_count produces int in CachedPageData."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        (cache_dir / "snapshot_meta.json").write_text(
            json.dumps(
                {"version": SNAPSHOT_VERSION, "timestamp": 0, "page_count": 1, "section_count": 0}
            )
        )

        pages_data = {
            "content/post.md": {
                "content_hash": "abc",
                "parsed_html": "<p>Hello</p>",
                "toc": "",
                "toc_items": [],
                "reading_time": "5",
                "word_count": "250",
                "excerpt": "Short excerpt",
                "meta_description": "",
            }
        }
        (cache_dir / "snapshot_pages.json").write_text(json.dumps(pages_data))

        cache = SnapshotCache(cache_dir)
        result = cache.load_page_cache()

        assert result is not None
        cached = result["content/post.md"]
        assert cached.reading_time == 5
        assert isinstance(cached.reading_time, int)
        assert cached.word_count == 250
        assert isinstance(cached.word_count, int)
        assert cached.excerpt == "Short excerpt"

    def test_invalid_reading_time_falls_back_to_zero(self, tmp_path: Path) -> None:
        """Invalid reading_time coerces to 0."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        (cache_dir / "snapshot_meta.json").write_text(
            json.dumps(
                {"version": SNAPSHOT_VERSION, "timestamp": 0, "page_count": 1, "section_count": 0}
            )
        )

        pages_data = {
            "content/post.md": {
                "content_hash": "x",
                "parsed_html": "<p>x</p>",
                "reading_time": "bad",
                "word_count": "nope",
                "excerpt": "",
                "meta_description": "",
            }
        }
        (cache_dir / "snapshot_pages.json").write_text(json.dumps(pages_data))

        cache = SnapshotCache(cache_dir)
        result = cache.load_page_cache()

        assert result is not None
        cached = result["content/post.md"]
        assert cached.reading_time == 0
        assert cached.word_count == 0


# =============================================================================
# apply_cached_parsing round-trip
# =============================================================================


class TestApplyCachedParsingTypeSafety:
    """Verify apply_cached_parsing produces page with int reading_time/word_count."""

    def test_applied_cache_values_usable_in_comparisons(self) -> None:
        """Page from cache has int reading_time/word_count for template comparisons."""
        content = "# Title\n\nBody"
        page = SimpleNamespace(
            source_path=Path("content/post.md"),
            _source=content,
            content=content,
            html_content="",
            toc="",
            _toc_items_cache=[],
            _reading_time=None,
            _word_count=None,
            _excerpt=None,
            _meta_description=None,
        )

        cached = CachedPageData(
            content_hash=compute_content_hash(content),
            parsed_html="<p>Body</p>",
            reading_time=5,
            word_count=250,
            excerpt="Short excerpt",
        )

        cache = {"content/post.md": cached}
        _pages_to_parse, pages_from_cache, hits = apply_cached_parsing([page], cache)

        assert hits == 1
        assert page in pages_from_cache
        assert page._reading_time == 5
        assert page._word_count == 250
        assert page._excerpt == "Short excerpt"
        # Usable in comparisons
        assert page._reading_time > 0
        assert page._word_count >= 100


# =============================================================================
# Content snapshot with string reading_time/word_count
# =============================================================================


class TestContentSnapshotTypeCoercion:
    """Verify _snapshot_page_initial coerces string reading_time/word_count."""

    def test_snapshot_page_initial_coerces_string_reading_metrics(self, tmp_path: Path) -> None:
        """Page with string reading_time/word_count produces PageSnapshot with ints."""
        from bengal.core.site import Site
        from bengal.snapshots.content import _snapshot_page_initial

        (tmp_path / "content").mkdir(parents=True)
        (tmp_path / "content" / "post.md").write_text("# Post\n\nBody")
        site = Site(root_path=tmp_path, config={"title": "Test"})
        page = SimpleNamespace(
            title="Post",
            metadata={},
            href="/post/",
            _path="/post/",
            output_path=tmp_path / "public/post/index.html",
            source_path=tmp_path / "content/post.md",
            content="# Post\n\nBody",
            _source="# Post\n\nBody",
            html_content="<p>Body</p>",
            toc="",
            toc_items=[],
            excerpt="Short",
            meta_description="",
            reading_time="5",
            word_count="250",
            tags=[],
            categories=[],
        )

        snapshot = _snapshot_page_initial(page, site)

        assert snapshot.reading_time == 5
        assert isinstance(snapshot.reading_time, int)
        assert snapshot.word_count == 250
        assert isinstance(snapshot.word_count, int)
        assert snapshot.reading_time > 0
        assert snapshot.word_count >= 100


# =============================================================================
# PostView + post_card render with page from cache
# =============================================================================


class TestPostCardRenderWithPageFromCache:
    """Render post_card with page that has cache-restored data; no TypeError."""

    def test_post_view_and_render_with_string_reading_time_from_old_cache(
        self, tmp_path: Path
    ) -> None:
        """Page with string _reading_time/_word_count (old cache) renders without TypeError."""
        pytest.importorskip("kida", reason="Template engine requires kida")

        from bengal.core.site import Site
        from bengal.rendering.template_engine import TemplateEngine

        # Simulate page from OLD cache before coercion: values arrived as strings
        page = SimpleNamespace(
            title="Old Cache Post",
            href="/old-cache/",
            _path="/old-cache/",
            date=None,
            metadata={},
            params={},
            excerpt="Excerpt text.",
            _excerpt="Excerpt text.",
            reading_time="3",
            _reading_time="3",
            word_count="150",
            _word_count="150",
            tags=[],
            draft=False,
        )

        site = Site(root_path=tmp_path, config={"title": "Test"})
        engine = TemplateEngine(site)

        # Template uses p.reading_time > 0 - PostView.from_page must coerce
        html = engine.render_string(
            "{% set p = post | post_view %}{% if p %}reading: {{ p.reading_time }} min{% end %}",
            {"post": page},
        )
        assert "reading: 3 min" in html

    def test_post_view_and_render_with_cache_restored_page(self, tmp_path: Path) -> None:
        """Page with _reading_time/_word_count from cache renders post_card without TypeError."""
        pytest.importorskip("kida", reason="Template engine requires kida")

        from bengal.core.site import Site
        from bengal.rendering.template_engine import TemplateEngine
        from bengal.rendering.template_functions.blog import PostView

        # Simulate page restored from cache (CachedPageData now coerces at load)
        page = SimpleNamespace(
            title="Test Post",
            href="/test-post/",
            _path="/test-post/",
            date=None,
            metadata={},
            params={},
            excerpt="This is the excerpt for the card.",
            _excerpt="This is the excerpt for the card.",
            reading_time=3,
            _reading_time=3,
            word_count=150,
            _word_count=150,
            tags=[],
            draft=False,
        )

        # PostView.from_page coerces; template uses p.reading_time > 0
        pv = PostView.from_page(page)
        assert pv.reading_time == 3
        assert pv.word_count == 150
        assert pv.reading_time > 0

        site = Site(root_path=tmp_path, config={"title": "Test"})
        engine = TemplateEngine(site)

        # Render template that uses p.reading_time > 0 and card_excerpt_html
        html = engine.render_string(
            "{% set p = post | post_view %}"
            "{% if p %}"
            "reading: {{ p.reading_time }} min, "
            "excerpt: {{ p.excerpt | card_excerpt_html(5, p.title, p.description) | safe }}"
            "{% end %}",
            {"post": page},
        )
        assert "reading: 3 min" in html
        assert "excerpt" in html


# =============================================================================
# Parser-version / config-hash gating (issue #377)
# =============================================================================


def _make_snapshot_stub() -> SimpleNamespace:
    """Minimal SiteSnapshot stand-in for SnapshotCache.save()."""
    page = SimpleNamespace(
        source_path=Path("content/post.md"),
        content_hash="abc",
        parsed_html="<p>Hello</p>",
        toc="",
        toc_items=(),
        reading_time=5,
        word_count=250,
        excerpt="Short",
        meta_description="",
    )
    return SimpleNamespace(page_count=1, section_count=0, pages=[page])


class TestSnapshotCacheParserConfigGating:
    """Verify load_page_cache() rejects the cache on parser/config drift (#377)."""

    def test_save_persists_parser_version_and_config_hash(self, tmp_path: Path) -> None:
        """save() writes parser_version and config_hash into snapshot_meta.json."""
        cache_dir = tmp_path / "cache"
        cache = SnapshotCache(cache_dir)
        cache.save(
            _make_snapshot_stub(),
            parser_version="markdown-3.6-toc2",
            config_hash="deadbeefcafe0000",
        )

        meta = json.loads((cache_dir / "snapshot_meta.json").read_text())
        assert meta["parser_version"] == "markdown-3.6-toc2"
        assert meta["config_hash"] == "deadbeefcafe0000"

    def test_load_hit_when_parser_and_config_match(self, tmp_path: Path) -> None:
        """Matching parser_version + config_hash yields a cache hit."""
        cache_dir = tmp_path / "cache"
        cache = SnapshotCache(cache_dir)
        cache.save(
            _make_snapshot_stub(),
            parser_version="markdown-3.6-toc2",
            config_hash="deadbeefcafe0000",
        )

        result = cache.load_page_cache(
            parser_version="markdown-3.6-toc2",
            config_hash="deadbeefcafe0000",
        )
        assert result is not None
        assert "content/post.md" in result

    def test_load_miss_on_parser_version_change(self, tmp_path: Path) -> None:
        """A changed parser_version is a whole-cache miss (no stale parsed_html)."""
        cache_dir = tmp_path / "cache"
        cache = SnapshotCache(cache_dir)
        cache.save(
            _make_snapshot_stub(),
            parser_version="markdown-3.6-toc2",
            config_hash="deadbeefcafe0000",
        )

        result = cache.load_page_cache(
            parser_version="markdown-3.6-toc3",  # bumped TOC_EXTRACTION_VERSION
            config_hash="deadbeefcafe0000",
        )
        assert result is None

    def test_load_miss_on_config_hash_change(self, tmp_path: Path) -> None:
        """A changed config_hash is a whole-cache miss (no stale parsed_html)."""
        cache_dir = tmp_path / "cache"
        cache = SnapshotCache(cache_dir)
        cache.save(
            _make_snapshot_stub(),
            parser_version="markdown-3.6-toc2",
            config_hash="deadbeefcafe0000",
        )

        result = cache.load_page_cache(
            parser_version="markdown-3.6-toc2",
            config_hash="1111222233334444",  # markdown/directive config changed
        )
        assert result is None

    def test_load_miss_when_legacy_meta_lacks_fields(self, tmp_path: Path) -> None:
        """Old snapshot_meta.json (no parser_version/config_hash) misses under new build."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        # Legacy meta: only the pre-#377 fields.
        (cache_dir / "snapshot_meta.json").write_text(
            json.dumps(
                {"version": SNAPSHOT_VERSION, "timestamp": 0, "page_count": 1, "section_count": 0}
            )
        )
        (cache_dir / "snapshot_pages.json").write_text(
            json.dumps(
                {
                    "content/post.md": {
                        "content_hash": "abc",
                        "parsed_html": "<p>Hello</p>",
                    }
                }
            )
        )

        cache = SnapshotCache(cache_dir)
        # A current build supplying values must treat the legacy (None) fields as a miss.
        result = cache.load_page_cache(
            parser_version="markdown-3.6-toc2",
            config_hash="deadbeefcafe0000",
        )
        assert result is None

    def test_load_skips_gates_when_args_omitted(self, tmp_path: Path) -> None:
        """Backward compat: omitting parser_version/config_hash skips the new gates."""
        cache_dir = tmp_path / "cache"
        cache = SnapshotCache(cache_dir)
        cache.save(
            _make_snapshot_stub(),
            parser_version="markdown-3.6-toc2",
            config_hash="deadbeefcafe0000",
        )

        # No gating args -> falls back to SNAPSHOT_VERSION-only behavior (hit).
        result = cache.load_page_cache()
        assert result is not None
        assert "content/post.md" in result
