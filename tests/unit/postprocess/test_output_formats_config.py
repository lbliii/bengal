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
from unittest.mock import Mock

import pytest

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

    # Helper methods

    def _create_mock_site(self, site_dir: Path, output_dir: Path, baseurl: str = "") -> Mock:
        """Create a mock Site instance."""
        site = Mock()
        site.site_dir = site_dir
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
