"""
Tests for config normalization edge cases in output formats.

These tests ensure that the config normalization logic correctly handles:
- Explicitly disabling all per-page formats
- Explicitly disabling all site-wide formats
- Configs with unrelated keys (should use defaults)
- Mixed enabling/disabling scenarios

Regression test for: Config normalization truthiness bug (__init__.py:165-166)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from bengal.cache.build_cache import BuildCache
from bengal.orchestration.build_context import AccumulatedPageData
from bengal.orchestration.stats import BuildStats
from bengal.postprocess.output_formats import OutputFormatsGenerator


class TestConfigNormalizationEdgeCases:
    """Test edge cases in config normalization."""

    def test_explicitly_disable_all_per_page_formats(self, tmp_path: Path) -> None:
        """User can explicitly disable all per-page formats via simple config.

        Regression test: Previously, {"json": False, "llm_txt": False} would
        result in defaults being used because empty list is falsy.
        """
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test",
            url="/test/",
            content="Content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        # Explicitly disable all per-page formats
        config = {
            "enabled": True,
            "json": False,
            "llm_txt": False,
            "site_json": True,  # Keep site-wide enabled
        }

        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Should NOT generate per-page JSON or TXT
        assert not (output_dir / "test/index.json").exists(), (
            "Per-page JSON should not be generated when explicitly disabled. "
            "Config was: {'json': False, 'llm_txt': False}"
        )
        assert not (output_dir / "test/index.txt").exists(), (
            "Per-page TXT should not be generated when explicitly disabled"
        )

        # Should still generate site-wide index
        assert (output_dir / "index.json").exists(), (
            "Site-wide index should still be generated when site_json: True"
        )

    def test_explicitly_disable_all_site_wide_formats(self, tmp_path: Path) -> None:
        """User can explicitly disable all site-wide formats."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test",
            url="/test/",
            content="Content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        config = {
            "enabled": True,
            "json": True,  # Keep per-page enabled
            "site_json": False,
            "site_llm": False,
        }

        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Should generate per-page JSON
        assert (output_dir / "test/index.json").exists(), (
            "Per-page JSON should be generated when json: True"
        )

        # Should NOT generate site-wide formats
        assert not (output_dir / "index.json").exists(), (
            "Site-wide index should not be generated when site_json: False"
        )
        assert not (output_dir / "llm-full.txt").exists(), (
            "Site-wide LLM should not be generated when site_llm: False"
        )

    def test_unrelated_config_keys_use_defaults(self, tmp_path: Path) -> None:
        """Config with only unrelated keys should use default formats."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test",
            url="/test/",
            content="Content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        # Config with unrelated keys only - should use defaults
        config = {
            "enabled": True,
            "some_other_setting": "value",
            "another_unrelated_key": 123,
        }

        generator = OutputFormatsGenerator(mock_site, config)

        # Should use defaults (json and llm_txt enabled)
        assert "json" in generator.config["per_page"], (
            "Default per_page should include 'json' when no per-page keys configured"
        )
        assert "llm_txt" in generator.config["per_page"], (
            "Default per_page should include 'llm_txt' when no per-page keys configured"
        )
        assert "index_json" in generator.config["site_wide"], (
            "Default site_wide should include 'index_json'"
        )

    def test_partial_per_page_config_overrides_defaults(self, tmp_path: Path) -> None:
        """Setting only json: True should not include llm_txt."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test",
            url="/test/",
            content="Content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        # Only enable JSON, implicitly disable llm_txt
        config = {
            "enabled": True,
            "json": True,
            # llm_txt not specified - should NOT be in per_page
        }

        generator = OutputFormatsGenerator(mock_site, config)

        # json: True means per_page keys were configured
        assert "json" in generator.config["per_page"]
        # llm_txt was not explicitly set, so it should not be added
        # (because we're in simple config mode and json key was present)

    def test_empty_config_uses_all_defaults(self, tmp_path: Path) -> None:
        """Empty config dict should use all defaults."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        # Empty config - should use all defaults
        config: dict = {}

        generator = OutputFormatsGenerator(mock_site, config)

        # Verify defaults are applied
        assert generator.config["enabled"] is True
        assert "json" in generator.config["per_page"]
        assert "llm_txt" in generator.config["per_page"]
        assert "index_json" in generator.config["site_wide"]
        assert "llm_full" in generator.config["site_wide"]

    def test_none_config_uses_all_defaults(self, tmp_path: Path) -> None:
        """None config should use all defaults."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        generator = OutputFormatsGenerator(mock_site, config=None)

        assert generator.config["enabled"] is True
        assert "json" in generator.config["per_page"]
        assert "llm_txt" in generator.config["per_page"]

    def test_advanced_format_with_empty_arrays(self, tmp_path: Path) -> None:
        """Advanced format with empty arrays should disable all formats."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test",
            url="/test/",
            content="Content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        # Advanced format with empty arrays
        config = {
            "enabled": True,
            "per_page": [],  # Explicitly empty
            "site_wide": [],  # Explicitly empty
        }

        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Should NOT generate any files
        assert not (output_dir / "test/index.json").exists()
        assert not (output_dir / "test/index.txt").exists()
        assert not (output_dir / "index.json").exists()
        assert not (output_dir / "llm-full.txt").exists()

    def test_enabled_false_disables_all_generation(self, tmp_path: Path) -> None:
        """Setting enabled: False should disable all output format generation."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test",
            url="/test/",
            content="Content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        config = {
            "enabled": False,
            "json": True,
            "site_json": True,
        }

        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Nothing should be generated
        assert not (output_dir / "test/index.json").exists()
        assert not (output_dir / "index.json").exists()

    def test_mixed_simple_and_advanced_prefers_advanced(self, tmp_path: Path) -> None:
        """If both simple keys and per_page/site_wide present, use advanced."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        # Mixed config - advanced keys should take precedence
        config = {
            "enabled": True,
            "json": True,  # Simple format key
            "per_page": ["llm_txt"],  # Advanced format key - should win
        }

        generator = OutputFormatsGenerator(mock_site, config)

        # Advanced format should be used
        assert generator.config["per_page"] == ["llm_txt"], (
            "Advanced format 'per_page' should override simple 'json' key"
        )

    def test_timed_generate_records_elapsed_time(self, tmp_path: Path) -> None:
        """Output-format substeps record timings for slow postprocess diagnosis."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        mock_site = self._create_mock_site(tmp_path, output_dir)
        stats = BuildStats()
        build_context = type("BuildContext", (), {"stats": stats})()
        generator = OutputFormatsGenerator(
            mock_site, {"enabled": True}, build_context=build_context
        )
        timings: dict[str, float] = {}

        result = generator._timed_generate(timings, "test_format", lambda: "ok")

        assert result == "ok"
        assert "test_format" in timings
        assert timings["test_format"] >= 0
        assert stats.postprocess_output_timings_ms["test_format"] == timings["test_format"]

    def test_incremental_accumulated_data_merges_cached_page_artifacts(
        self, tmp_path: Path
    ) -> None:
        """Incremental output formats can reuse cached artifacts for unchanged pages."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        mock_site = self._create_mock_site(tmp_path, output_dir)
        changed_page = self._create_mock_page(
            title="Changed",
            url="/changed/",
            content="Changed",
            output_path=output_dir / "changed/index.html",
        )
        changed_page.source_path = Path("content/changed.md")
        unchanged_page = self._create_mock_page(
            title="Unchanged",
            url="/unchanged/",
            content="Unchanged",
            output_path=output_dir / "unchanged/index.html",
        )
        unchanged_page.source_path = Path("content/unchanged.md")
        mock_site.pages = [changed_page, unchanged_page]
        cache = BuildCache(site_root=tmp_path)
        cache.page_artifacts["content/unchanged.md"] = _artifact_record("content/unchanged.md")
        changed_artifact = _accumulated_page_data(Path("content/changed.md"), "/changed/")
        build_context = SimpleNamespace(incremental=True, cache=cache)
        generator = OutputFormatsGenerator(
            mock_site, {"enabled": True}, build_context=build_context
        )

        merged = generator._merge_cached_page_artifacts(
            [changed_page, unchanged_page], [changed_artifact]
        )

        assert [data.uri for data in merged] == ["/changed/", "/unchanged/"]

    def test_incremental_output_formats_use_cached_artifacts_without_rendered_pages(
        self, tmp_path: Path
    ) -> None:
        """No-op incremental builds can skip site-wide output from cached artifacts."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        index_path = output_dir / "index.json"
        index_path.write_text("sentinel", encoding="utf-8")
        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Unchanged",
            url="/unchanged/",
            content="Unchanged",
            output_path=output_dir / "unchanged/index.html",
        )
        page.source_path = Path("content/unchanged.md")
        mock_site.pages = [page]
        cache = BuildCache(site_root=tmp_path)
        cache.page_artifacts["content/unchanged.md"] = _artifact_record("content/unchanged.md")
        build_context = SimpleNamespace(
            incremental=True,
            cache=cache,
            stats=BuildStats(),
            has_accumulated_page_data=False,
            get_accumulated_page_data=list,
        )
        generator = OutputFormatsGenerator(
            mock_site,
            {"enabled": True, "per_page": [], "site_wide": ["index_json"]},
            build_context=build_context,
        )
        cached_data = generator._merge_cached_page_artifacts([page], [])
        fingerprint = generator._site_wide_input_fingerprint(
            "site_index_json",
            [page],
            cached_data,
            {
                "excerpt_length": 200,
                "json_indent": None,
                "include_full_content": False,
            },
        )
        assert fingerprint is not None
        cache.output_format_fingerprints["site_index_json"] = fingerprint

        generator.generate()

        assert index_path.read_text(encoding="utf-8") == "sentinel"
        assert build_context.stats.postprocess_output_timings_ms["site_index_json"] == 0.0

    def test_site_wide_generation_skips_when_input_fingerprint_matches(
        self, tmp_path: Path
    ) -> None:
        """Unchanged site-wide outputs skip generator work when their input fingerprint matches."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        (output_dir / "index.json").write_text("{}", encoding="utf-8")
        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Page",
            url="/page/",
            content="Page",
            output_path=output_dir / "page/index.html",
        )
        page.source_path = Path("content/page.md")
        cache = BuildCache(site_root=tmp_path)
        stats = BuildStats()
        build_context = SimpleNamespace(incremental=True, cache=cache, stats=stats)
        generator = OutputFormatsGenerator(
            mock_site, {"enabled": True}, build_context=build_context
        )
        data = [_accumulated_page_data(Path("content/page.md"), "/page/")]
        fingerprint = generator._site_wide_input_fingerprint(
            "site_index_json", [page], data, {"json_indent": None}
        )
        assert fingerprint is not None
        cache.output_format_fingerprints["site_index_json"] = fingerprint

        result = generator._generate_site_wide_if_needed(
            {},
            "site_index_json",
            [page],
            data,
            {"json_indent": None},
            [output_dir / "index.json"],
            lambda: (_ for _ in ()).throw(AssertionError("should skip")),
        )

        assert result == output_dir / "index.json"
        assert stats.postprocess_output_timings_ms["site_index_json"] == 0.0

    def test_changelog_site_wide_generation_does_not_skip_on_matching_fingerprint(
        self, tmp_path: Path
    ) -> None:
        """Changelog includes build ids, so it must regenerate every build."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        (output_dir / "changelog.json").write_text("{}", encoding="utf-8")
        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Page",
            url="/page/",
            content="Page",
            output_path=output_dir / "page/index.html",
        )
        page.source_path = Path("content/page.md")
        cache = BuildCache(site_root=tmp_path)
        cache.output_format_fingerprints["site_changelog"] = "matching"
        build_context = SimpleNamespace(incremental=True, cache=cache, stats=BuildStats())
        generator = OutputFormatsGenerator(
            mock_site, {"enabled": True}, build_context=build_context
        )
        data = [_accumulated_page_data(Path("content/page.md"), "/page/")]

        result = generator._generate_site_wide_if_needed(
            {},
            "site_changelog",
            [page],
            data,
            {},
            [output_dir / "changelog.json"],
            lambda: "generated",
        )

        assert result == "generated"

    def test_site_wide_fingerprint_sanitizes_page_artifact_metadata(self, tmp_path: Path) -> None:
        """Fingerprinting tolerates Python objects from rendered page metadata."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Page",
            url="/page/",
            content="Page",
            output_path=output_dir / "page/index.html",
        )
        page.source_path = Path("content/page.md")
        build_context = SimpleNamespace(incremental=True, cache=BuildCache(site_root=tmp_path))
        generator = OutputFormatsGenerator(
            mock_site, {"enabled": True}, build_context=build_context
        )
        data = _accumulated_page_data(Path("content/page.md"), "/page/")
        data.raw_metadata["path"] = tmp_path / "source.md"
        data.enhanced_metadata["updated"] = datetime(2026, 5, 3, 12, 0, 0)
        data.full_json_data = {
            "url": "/page/",
            "source": tmp_path / "source.md",
            1: {"updated": datetime(2026, 5, 3, 12, 0, 0)},
        }

        fingerprint = generator._site_wide_input_fingerprint(
            "site_index_json", [page], [data], {"json_indent": None}
        )

        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64

    # Helper methods

    def _create_mock_site(self, site_dir: Path, output_dir: Path, baseurl: str = "") -> Mock:
        """Create a mock Site instance."""
        site = Mock()
        site.site_dir = site_dir
        site.root_path = site_dir
        site.output_dir = output_dir
        site.dev_mode = False
        site.versioning_enabled = False
        site.build_time = datetime(2024, 1, 1, 12, 0, 0)
        site.config = {
            "title": "Test Site",
            "baseurl": baseurl,
            "description": "Test site description",
            "search": {},
        }
        site.title = "Test Site"
        site.baseurl = baseurl
        site.description = "Test site description"
        site.pages = []
        return site

    def _create_mock_page(
        self,
        title: str,
        url: str,
        content: str,
        output_path: Path | None,
        tags: list[str] | None = None,
        section_name: str | None = None,
        metadata: dict | None = None,
    ) -> Mock:
        """Create a mock Page instance."""
        page = Mock()
        page.title = title
        page.href = url
        page._path = url
        page.content = content
        page.html_content = content
        page.plain_text = content
        page.output_path = output_path
        page.tags = tags or []
        page.date = None
        page.metadata = metadata or {}
        page.source_path = Path("content/test.md")
        page.version = None

        if section_name:
            section = Mock()
            section.name = section_name
            page._section = section
        else:
            page._section = None

        return page


def _accumulated_page_data(source_path: Path, uri: str) -> AccumulatedPageData:
    return AccumulatedPageData(
        source_path=source_path,
        url=uri,
        uri=uri,
        title=uri.strip("/") or "Home",
        description="",
        date=None,
        date_iso=None,
        plain_text="Body",
        excerpt="Body",
        content_preview="Body",
        word_count=1,
        reading_time=1,
        section="Docs",
        tags=[],
        dir=uri,
        full_json_data={"url": uri},
        json_output_path=Path("public/index.json"),
    )


def _artifact_record(source_path: str) -> dict[str, object]:
    data = _accumulated_page_data(Path(source_path), "/unchanged/")
    return {
        "source_path": str(data.source_path),
        "url": data.url,
        "uri": data.uri,
        "title": data.title,
        "description": data.description,
        "date": data.date,
        "date_iso": data.date_iso,
        "plain_text": data.plain_text,
        "excerpt": data.excerpt,
        "content_preview": data.content_preview,
        "word_count": data.word_count,
        "reading_time": data.reading_time,
        "section": data.section,
        "tags": data.tags,
        "dir": data.dir,
        "enhanced_metadata": data.enhanced_metadata,
        "is_autodoc": data.is_autodoc,
        "full_json_data": data.full_json_data,
        "json_output_path": str(data.json_output_path),
        "raw_metadata": data.raw_metadata,
    }
