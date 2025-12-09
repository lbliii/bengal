"""Tests for output validator.

Tests health/validators/output.py:
- OutputValidator: build output validation in health check system
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.output import OutputValidator


@pytest.fixture
def validator():
    """Create OutputValidator instance."""
    return OutputValidator()


@pytest.fixture
def mock_site(tmp_path):
    """Create mock site with output directory."""
    site = MagicMock()
    site.output_dir = tmp_path / "public"
    site.output_dir.mkdir(parents=True, exist_ok=True)
    site.config = {"min_page_size": 1000, "theme": "default"}

    # Create mock pages
    site.pages = []

    return site


def create_page(output_dir: Path, name: str, content: str):
    """Helper to create a mock page with output file."""
    output_path = output_dir / name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)

    page = MagicMock()
    page.output_path = output_path
    return page


class TestOutputValidatorBasics:
    """Tests for OutputValidator basic attributes."""

    def test_has_name(self, validator):
        """Validator has a name."""
        assert validator.name == "Output"

    def test_has_description(self, validator):
        """Validator has a description."""
        assert validator.description == "Validates generated pages and assets"

    def test_enabled_by_default(self, validator):
        """Validator is enabled by default."""
        assert validator.enabled_by_default is True


class TestOutputValidatorPageSizes:
    """Tests for page size validation."""

    def test_no_warning_for_adequate_pages(self, validator, mock_site, tmp_path):
        """No warning when pages have adequate size."""
        # Create page with sufficient content
        page = create_page(mock_site.output_dir, "index.html", "x" * 2000)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        size_warnings = [r for r in warning_results if "small" in r.message.lower()]
        assert len(size_warnings) == 0

    def test_warning_for_small_pages(self, validator, mock_site, tmp_path):
        """Warning when pages are suspiciously small."""
        # Create small page
        page = create_page(mock_site.output_dir, "small.html", "tiny")
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("small" in r.message.lower() for r in warning_results)

    def test_small_pages_have_details(self, validator, mock_site, tmp_path):
        """Small page warnings include file details."""
        page = create_page(mock_site.output_dir, "tiny.html", "x")
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        small_warning = next((r for r in warning_results if "small" in r.message.lower()), None)
        assert small_warning is not None
        assert small_warning.details is not None

    def test_uses_config_min_size(self, validator, mock_site, tmp_path):
        """Uses min_page_size from config."""
        mock_site.config["min_page_size"] = 500

        # Create page that's under 500 bytes
        page = create_page(mock_site.output_dir, "medium.html", "x" * 400)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("small" in r.message.lower() for r in warning_results)


class TestOutputValidatorAssets:
    """Tests for asset validation."""

    def test_error_when_no_assets_dir(self, validator, mock_site, tmp_path):
        """Error when assets directory doesn't exist."""
        # Don't create assets directory
        results = validator.validate(mock_site)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert any("assets" in r.message.lower() for r in error_results)

    def test_warning_when_no_css_files(self, validator, mock_site, tmp_path):
        """Warning when no CSS files in output."""
        assets_dir = mock_site.output_dir / "assets" / "css"
        assets_dir.mkdir(parents=True, exist_ok=True)
        # Don't create any CSS files

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("css" in r.message.lower() for r in warning_results)

    def test_no_warning_when_css_present(self, validator, mock_site, tmp_path):
        """No warning when CSS files present."""
        css_dir = mock_site.output_dir / "assets" / "css"
        css_dir.mkdir(parents=True, exist_ok=True)
        (css_dir / "style.css").write_text("body { color: black; }")

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        css_warnings = [r for r in warning_results if "css" in r.message.lower()]
        assert len(css_warnings) == 0

    def test_warning_when_no_js_for_default_theme(self, validator, mock_site, tmp_path):
        """Warning when no JS files for default theme."""
        mock_site.config["theme"] = "default"
        assets_dir = mock_site.output_dir / "assets"
        (assets_dir / "css").mkdir(parents=True, exist_ok=True)
        (assets_dir / "js").mkdir(parents=True, exist_ok=True)
        # Create CSS but no JS
        (assets_dir / "css" / "style.css").write_text("body {}")

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("js" in r.message.lower() for r in warning_results)


class TestOutputValidatorDirectory:
    """Tests for output directory validation."""

    def test_error_when_output_dir_missing(self, validator, tmp_path):
        """Error when output directory doesn't exist."""
        site = MagicMock()
        site.output_dir = tmp_path / "nonexistent"
        site.config = {"min_page_size": 1000, "theme": "default"}
        site.pages = []

        results = validator.validate(site)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert any("does not exist" in r.message for r in error_results)


class TestOutputValidatorStats:
    """Tests for validator stats tracking."""

    def test_tracks_pages_total(self, validator, mock_site, tmp_path):
        """Tracks total HTML files in stats."""
        # Create some HTML files
        (mock_site.output_dir / "index.html").write_text("<html></html>")
        (mock_site.output_dir / "about.html").write_text("<html></html>")

        validator.validate(mock_site)

        assert validator.last_stats is not None
        assert validator.last_stats.pages_total == 2

    def test_tracks_sub_timings(self, validator, mock_site, tmp_path):
        """Tracks sub-operation timings."""
        # Create minimal structure
        (mock_site.output_dir / "assets" / "css").mkdir(parents=True)
        (mock_site.output_dir / "assets" / "css" / "style.css").write_text("")

        validator.validate(mock_site)

        assert validator.last_stats is not None
        assert "page_sizes" in validator.last_stats.sub_timings
        assert "assets" in validator.last_stats.sub_timings
        assert "directory" in validator.last_stats.sub_timings

    def test_tracks_asset_metrics(self, validator, mock_site, tmp_path):
        """Tracks asset file counts in metrics."""
        css_dir = mock_site.output_dir / "assets" / "css"
        js_dir = mock_site.output_dir / "assets" / "js"
        css_dir.mkdir(parents=True)
        js_dir.mkdir(parents=True)
        (css_dir / "style.css").write_text("")
        (js_dir / "main.js").write_text("")

        validator.validate(mock_site)

        assert validator.last_stats.metrics["css_files"] == 1
        assert validator.last_stats.metrics["js_files"] == 1


class TestOutputValidatorRecommendations:
    """Tests for recommendation messages."""

    def test_small_page_has_recommendation(self, validator, mock_site, tmp_path):
        """Small page warning has recommendation."""
        page = create_page(mock_site.output_dir, "tiny.html", "x")
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        small_warning = next((r for r in warning_results if "small" in r.message.lower()), None)
        assert small_warning is not None
        assert small_warning.recommendation is not None

    def test_no_assets_has_recommendation(self, validator, mock_site, tmp_path):
        """No assets error has recommendation."""
        results = validator.validate(mock_site)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assets_error = next((r for r in error_results if "assets" in r.message.lower()), None)
        assert assets_error is not None
        assert assets_error.recommendation is not None


class TestOutputValidatorSilenceIsGolden:
    """Tests that validator follows 'silence is golden' principle."""

    def test_no_success_for_adequate_sizes(self, validator, mock_site, tmp_path):
        """No explicit success for adequate page sizes."""
        page = create_page(mock_site.output_dir, "index.html", "x" * 2000)
        mock_site.pages = [page]
        (mock_site.output_dir / "assets" / "css").mkdir(parents=True)
        (mock_site.output_dir / "assets" / "css" / "style.css").write_text("")

        results = validator.validate(mock_site)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        size_success = [r for r in success_results if "size" in r.message.lower()]
        assert len(size_success) == 0

    def test_no_success_for_present_assets(self, validator, mock_site, tmp_path):
        """No explicit success for present assets."""
        (mock_site.output_dir / "assets" / "css").mkdir(parents=True)
        (mock_site.output_dir / "assets" / "css" / "style.css").write_text("")
        (mock_site.output_dir / "assets" / "js").mkdir(parents=True)
        (mock_site.output_dir / "assets" / "js" / "main.js").write_text("")

        results = validator.validate(mock_site)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        # Should not have CSS/JS success messages
        asset_success = [
            r for r in success_results if "css" in r.message.lower() or "js" in r.message.lower()
        ]
        assert len(asset_success) == 0
