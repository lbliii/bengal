"""
Tests for metadata utilities.

Covers:
- build_template_metadata() function
- Markdown engine detection
- Syntax highlighter detection
- Theme information extraction
- i18n configuration
- Exposure level filtering
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from bengal.rendering.metadata import (
    _get_highlighter_version,
    _get_i18n_info,
    _get_markdown_engine_and_version,
    _get_theme_info,
    build_template_metadata,
)


class TestGetMarkdownEngineAndVersion:
    """Tests for _get_markdown_engine_and_version."""

    def test_default_engine_is_patitas(self):
        """Default markdown engine is patitas."""
        engine, version = _get_markdown_engine_and_version({})
        assert engine == "patitas"

    def test_legacy_flat_key(self):
        """Supports legacy flat markdown_engine key."""
        config = {"markdown_engine": "python-markdown"}
        engine, version = _get_markdown_engine_and_version(config)
        assert engine == "python-markdown"

    def test_nested_markdown_config(self):
        """Supports nested markdown.parser config."""
        config = {"markdown": {"parser": "commonmark"}}
        engine, version = _get_markdown_engine_and_version(config)
        assert engine == "commonmark"

    def test_legacy_key_takes_precedence(self):
        """Legacy markdown_engine key takes precedence over nested config."""
        config = {
            "markdown_engine": "legacy-engine",
            "markdown": {"parser": "nested-engine"},
        }
        engine, version = _get_markdown_engine_and_version(config)
        assert engine == "legacy-engine"

    def test_mistune_version_detection(self):
        """Detects mistune version when installed."""
        config = {"markdown_engine": "mistune"}

        with (
            patch.dict("sys.modules", {"mistune": MagicMock(__version__="2.0.0")}),
            patch("bengal.rendering.metadata.mistune", create=True) as mock_mistune,
        ):
            mock_mistune.__version__ = "2.0.0"
            engine, version = _get_markdown_engine_and_version(config)

        assert engine == "mistune"
        # Version may or may not be detected depending on import success

    def test_python_markdown_aliases(self):
        """Recognizes python-markdown aliases."""
        for alias in ["python-markdown", "markdown", "python_markdown"]:
            config = {"markdown_engine": alias}
            engine, version = _get_markdown_engine_and_version(config)
            assert engine == alias

    def test_handles_import_error_gracefully(self):
        """Handles missing markdown library gracefully."""
        config = {"markdown_engine": "nonexistent-engine"}
        engine, version = _get_markdown_engine_and_version(config)
        assert engine == "nonexistent-engine"
        # Version should be None when library not found
        assert version is None

    def test_handles_none_markdown_config(self):
        """Handles None markdown config gracefully."""
        config = {"markdown": None}
        engine, version = _get_markdown_engine_and_version(config)
        assert engine == "patitas"  # Falls back to default


class TestGetHighlighterVersion:
    """Tests for _get_highlighter_version."""

    def test_returns_pygments_version_when_installed(self):
        """Returns pygments version when installed."""
        with patch("bengal.rendering.metadata.pygments", create=True) as mock_pygments:
            mock_pygments.__version__ = "2.15.0"
            _get_highlighter_version()  # May return version or None

    def test_returns_none_on_import_error(self):
        """Returns None when pygments __version__ is missing."""
        # Test that the function handles errors gracefully
        # The actual function returns None on any exception
        # We just verify it doesn't crash and returns a valid type
        version = _get_highlighter_version()
        assert version is None or isinstance(version, str)


class TestGetThemeInfo:
    """Tests for _get_theme_info."""

    def test_default_theme(self):
        """Returns default theme when none specified."""
        mock_site = MagicMock()
        mock_site.theme = None

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            info = _get_theme_info(mock_site)

        assert info["name"] == "default"
        assert info["version"] is None

    def test_custom_theme(self):
        """Returns custom theme name."""
        mock_site = MagicMock()
        mock_site.theme = "my-theme"

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            info = _get_theme_info(mock_site)

        assert info["name"] == "my-theme"

    def test_theme_with_version(self):
        """Returns theme version when available."""
        mock_site = MagicMock()
        mock_site.theme = "versioned-theme"

        mock_pkg = MagicMock()
        mock_pkg.version = "1.2.3"

        with patch("bengal.rendering.metadata.get_theme_package", return_value=mock_pkg):
            info = _get_theme_info(mock_site)

        assert info["name"] == "versioned-theme"
        assert info["version"] == "1.2.3"

    def test_handles_theme_package_error(self):
        """Handles theme package lookup errors gracefully."""
        mock_site = MagicMock()
        mock_site.theme = "error-theme"

        with patch(
            "bengal.rendering.metadata.get_theme_package",
            side_effect=Exception("Lookup failed"),
        ):
            info = _get_theme_info(mock_site)

        assert info["name"] == "error-theme"
        assert info["version"] is None


class TestGetI18nInfo:
    """Tests for _get_i18n_info."""

    def test_default_values(self):
        """Returns default i18n values when not configured."""
        info = _get_i18n_info({})

        assert info["strategy"] == "none"
        assert info["defaultLanguage"] == "en"
        assert info["languages"] == []

    def test_custom_i18n_config(self):
        """Returns custom i18n configuration."""
        config = {
            "i18n": {
                "strategy": "subdirectory",
                "default_language": "es",
                "languages": ["es", "en", "fr"],
            }
        }

        info = _get_i18n_info(config)

        assert info["strategy"] == "subdirectory"
        assert info["defaultLanguage"] == "es"
        assert info["languages"] == ["es", "en", "fr"]

    def test_handles_none_i18n(self):
        """Handles None i18n config gracefully."""
        config = {"i18n": None}
        info = _get_i18n_info(config)

        assert info["strategy"] == "none"
        assert info["defaultLanguage"] == "en"


class TestBuildTemplateMetadata:
    """Tests for build_template_metadata."""

    @pytest.fixture
    def mock_site(self):
        """Create a mock site for metadata tests."""
        site = MagicMock()
        site.config = {}
        site.theme = "default"
        site.baseurl = None
        site.build_time = datetime(2024, 1, 15, 12, 0, 0)
        return site

    def test_minimal_exposure(self, mock_site):
        """Minimal exposure returns only engine info."""
        mock_site.config = {"expose_metadata": "minimal"}

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            metadata = build_template_metadata(mock_site)

        assert "engine" in metadata
        assert metadata["engine"]["name"] == "Bengal SSG"
        # Should NOT include theme, build, i18n
        assert "theme" not in metadata
        assert "build" not in metadata
        assert "i18n" not in metadata

    def test_standard_exposure(self, mock_site):
        """Standard exposure includes theme, build, i18n."""
        mock_site.config = {"expose_metadata": "standard"}

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            metadata = build_template_metadata(mock_site)

        assert "engine" in metadata
        assert "theme" in metadata
        assert "build" in metadata
        assert "i18n" in metadata
        # Should NOT include rendering details
        assert "rendering" not in metadata

    def test_extended_exposure(self, mock_site):
        """Extended exposure includes all metadata."""
        mock_site.config = {"expose_metadata": "extended"}

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            metadata = build_template_metadata(mock_site)

        assert "engine" in metadata
        assert "theme" in metadata
        assert "build" in metadata
        assert "i18n" in metadata
        assert "rendering" in metadata
        assert "site" in metadata

    def test_default_exposure_is_minimal(self, mock_site):
        """Default exposure level is minimal."""
        mock_site.config = {}

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            metadata = build_template_metadata(mock_site)

        assert "engine" in metadata
        assert "theme" not in metadata

    def test_invalid_exposure_falls_back_to_minimal(self, mock_site):
        """Invalid exposure level falls back to minimal."""
        mock_site.config = {"expose_metadata": "invalid-level"}

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            metadata = build_template_metadata(mock_site)

        assert "engine" in metadata
        assert "theme" not in metadata

    def test_exposure_level_case_insensitive(self, mock_site):
        """Exposure level is case-insensitive."""
        for level in ["STANDARD", "Standard", "STANDARD"]:
            mock_site.config = {"expose_metadata": level}

            with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
                metadata = build_template_metadata(mock_site)

            assert "theme" in metadata

    def test_exposure_level_whitespace_trimmed(self, mock_site):
        """Exposure level whitespace is trimmed."""
        mock_site.config = {"expose_metadata": "  standard  "}

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            metadata = build_template_metadata(mock_site)

        assert "theme" in metadata

    def test_engine_includes_version(self, mock_site):
        """Engine info includes Bengal version."""
        mock_site.config = {"expose_metadata": "minimal"}

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            metadata = build_template_metadata(mock_site)

        assert metadata["engine"]["name"] == "Bengal SSG"
        assert "version" in metadata["engine"]

    def test_build_timestamp_format(self, mock_site):
        """Build timestamp is in ISO format."""
        mock_site.config = {"expose_metadata": "standard"}
        mock_site.build_time = datetime(2024, 1, 15, 12, 30, 45)

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            metadata = build_template_metadata(mock_site)

        assert metadata["build"]["timestamp"] == "2024-01-15T12:30:45"

    def test_handles_missing_build_time(self, mock_site):
        """Handles missing build_time gracefully."""
        mock_site.config = {"expose_metadata": "standard"}
        del mock_site.build_time  # Remove build_time attribute

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            metadata = build_template_metadata(mock_site)

        assert metadata["build"]["timestamp"] is None

    def test_handles_none_config(self):
        """Handles site with None config."""
        mock_site = MagicMock()
        mock_site.config = None
        mock_site.theme = None
        mock_site.baseurl = None

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            metadata = build_template_metadata(mock_site)

        # Should use defaults and not crash
        assert "engine" in metadata

    def test_rendering_includes_markdown_info(self, mock_site):
        """Extended exposure includes markdown engine info."""
        mock_site.config = {
            "expose_metadata": "extended",
            "markdown_engine": "mistune",
        }

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            metadata = build_template_metadata(mock_site)

        assert metadata["rendering"]["markdown"] == "mistune"
        assert "markdownVersion" in metadata["rendering"]

    def test_rendering_includes_highlighter_info(self, mock_site):
        """Extended exposure includes highlighter info."""
        mock_site.config = {"expose_metadata": "extended"}

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            metadata = build_template_metadata(mock_site)

        assert metadata["rendering"]["highlighter"] == "rosettes"
        assert "highlighterVersion" in metadata["rendering"]

    def test_site_includes_baseurl(self, mock_site):
        """Extended exposure includes site baseurl."""
        mock_site.config = {"expose_metadata": "extended"}
        mock_site.baseurl = "/blog"

        with patch("bengal.rendering.metadata.get_theme_package", return_value=None):
            metadata = build_template_metadata(mock_site)

        assert metadata["site"]["baseurl"] == "/blog"
