"""Tests for rendering validator.

Tests health/validators/rendering.py:
- RenderingValidator: HTML output quality validation in health check system
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.rendering import RenderingValidator


@pytest.fixture
def validator():
    """Create RenderingValidator instance."""
    return RenderingValidator()


@pytest.fixture
def mock_site(tmp_path):
    """Create mock site with output pages."""
    site = MagicMock()
    site.output_dir = tmp_path / "public"
    site.output_dir.mkdir(parents=True, exist_ok=True)
    site.pages = []
    return site


def create_page(output_dir: Path, name: str, content: str, generated: bool = False):
    """Helper to create a mock page with output file."""
    output_path = output_dir / name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)

    page = MagicMock()
    page.output_path = output_path
    page.metadata = {"_generated": generated}
    return page


VALID_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="description" content="Test page">
    <title>Test Page</title>
</head>
<body>
    <h1>Test</h1>
</body>
</html>"""


class TestRenderingValidatorBasics:
    """Tests for RenderingValidator basic attributes."""

    def test_has_name(self, validator):
        """Validator has a name."""
        assert validator.name == "Rendering"

    def test_has_description(self, validator):
        """Validator has a description."""
        assert validator.description == "Validates HTML output quality and completeness"

    def test_enabled_by_default(self, validator):
        """Validator is enabled by default."""
        assert validator.enabled_by_default is True


class TestRenderingValidatorHTMLStructure:
    """Tests for HTML structure validation."""

    def test_success_for_valid_html(self, validator, mock_site, tmp_path):
        """Returns success for valid HTML structure."""
        page = create_page(mock_site.output_dir, "index.html", VALID_HTML)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert any("structure" in r.message.lower() for r in success_results)

    def test_warning_for_missing_doctype(self, validator, mock_site, tmp_path):
        """Returns warning for missing DOCTYPE."""
        html_without_doctype = "<html><head><title>Test</title></head><body></body></html>"
        page = create_page(mock_site.output_dir, "no-doctype.html", html_without_doctype)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("structure" in r.message.lower() for r in warning_results)

    def test_warning_for_missing_html_tag(self, validator, mock_site, tmp_path):
        """Returns warning for missing html tag."""
        no_html_tag = "<!DOCTYPE html><head><title>Test</title></head><body></body>"
        page = create_page(mock_site.output_dir, "no-html.html", no_html_tag)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        # Should have structure issues
        structure_warnings = [r for r in warning_results if "structure" in r.message.lower()]
        assert len(structure_warnings) >= 1

    def test_warning_has_details(self, validator, mock_site, tmp_path):
        """Structure warning includes file details."""
        no_doctype = "<html><body></body></html>"
        page = create_page(mock_site.output_dir, "bad.html", no_doctype)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        structure_warning = next(
            (r for r in warning_results if "structure" in r.message.lower()), None
        )
        if structure_warning:
            assert structure_warning.details is not None


class TestRenderingValidatorUnrenderedJinja2:
    """Tests for unrendered Jinja2 detection."""

    def test_success_when_no_unrendered(self, validator, mock_site, tmp_path):
        """Returns success when no unrendered Jinja2."""
        page = create_page(mock_site.output_dir, "clean.html", VALID_HTML)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert any("jinja2" in r.message.lower() for r in success_results)

    def test_warning_for_unrendered_page_variable(self, validator, mock_site, tmp_path):
        """Returns warning for unrendered {{ page. }} variables."""
        html_with_jinja = VALID_HTML.replace("Test", "{{ page.title }}")
        page = create_page(mock_site.output_dir, "unrendered.html", html_with_jinja)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("jinja2" in r.message.lower() for r in warning_results)

    def test_warning_for_unrendered_site_variable(self, validator, mock_site, tmp_path):
        """Returns warning for unrendered {{ site. }} variables."""
        html_with_jinja = VALID_HTML.replace("Test Page", "{{ site.title }}")
        page = create_page(mock_site.output_dir, "unrendered2.html", html_with_jinja)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("jinja2" in r.message.lower() for r in warning_results)


class TestRenderingValidatorSEOMetadata:
    """Tests for SEO metadata validation."""

    def test_success_when_seo_present(self, validator, mock_site, tmp_path):
        """Returns success when SEO metadata present."""
        page = create_page(mock_site.output_dir, "seo.html", VALID_HTML)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert any("seo" in r.message.lower() for r in success_results)

    def test_warning_for_missing_title(self, validator, mock_site, tmp_path):
        """Returns warning for missing title tag."""
        no_title = """<!DOCTYPE html>
<html><head><meta name="description" content="Test"></head><body></body></html>"""
        page = create_page(mock_site.output_dir, "no-title.html", no_title)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("seo" in r.message.lower() for r in warning_results)

    def test_warning_for_missing_description(self, validator, mock_site, tmp_path):
        """Returns warning for missing description."""
        no_description = """<!DOCTYPE html>
<html><head><title>Test</title></head><body></body></html>"""
        page = create_page(mock_site.output_dir, "no-desc.html", no_description)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert any("seo" in r.message.lower() for r in warning_results)

    def test_accepts_og_description(self, validator, mock_site, tmp_path):
        """Accepts og:description as alternative."""
        og_description = """<!DOCTYPE html>
<html><head><title>Test</title>
<meta property="og:description" content="OpenGraph desc"></head><body></body></html>"""
        page = create_page(mock_site.output_dir, "og-desc.html", og_description)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert any("seo" in r.message.lower() for r in success_results)

    def test_skips_generated_pages(self, validator, mock_site, tmp_path):
        """Skips generated pages in SEO check."""
        no_seo = "<!DOCTYPE html><html><head></head><body></body></html>"
        page = create_page(mock_site.output_dir, "generated.html", no_seo, generated=True)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        # Should not warn about SEO for generated pages
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        seo_warnings = [r for r in warning_results if "seo" in r.message.lower()]
        assert len(seo_warnings) == 0


class TestRenderingValidatorPrivateMethods:
    """Tests for private helper methods."""

    def test_detect_unrendered_jinja2_finds_page(self, validator):
        """_detect_unrendered_jinja2 finds {{ page. }}."""
        html = "<html><body>{{ page.title }}</body></html>"
        with patch("bengal.health.validators.rendering.ParserFactory") as MockParserFactory:
            mock_parser = MagicMock()
            mock_soup = MagicMock()
            mock_soup.get_text.return_value = "{{ page.title }}"
            mock_parser.return_value = mock_soup
            MockParserFactory.get_html_parser.return_value = mock_parser

            result = validator._detect_unrendered_jinja2(html)
            assert result is True

    def test_detect_unrendered_jinja2_finds_site(self, validator):
        """_detect_unrendered_jinja2 finds {{ site. }}."""
        html = "<html><body>{{ site.title }}</body></html>"
        with patch("bengal.health.validators.rendering.ParserFactory") as MockParserFactory:
            mock_parser = MagicMock()
            mock_soup = MagicMock()
            mock_soup.get_text.return_value = "{{ site.title }}"
            mock_parser.return_value = mock_soup
            MockParserFactory.get_html_parser.return_value = mock_parser

            result = validator._detect_unrendered_jinja2(html)
            assert result is True

    def test_detect_unrendered_jinja2_clean(self, validator):
        """_detect_unrendered_jinja2 returns False for clean HTML."""
        html = "<html><body>Hello World</body></html>"
        with patch("bengal.health.validators.rendering.ParserFactory") as MockParserFactory:
            mock_parser = MagicMock()
            mock_soup = MagicMock()
            mock_soup.get_text.return_value = "Hello World"
            mock_parser.return_value = mock_soup
            MockParserFactory.get_html_parser.return_value = mock_parser

            result = validator._detect_unrendered_jinja2(html)
            assert result is False


class TestRenderingValidatorRecommendations:
    """Tests for recommendation messages."""

    def test_structure_warning_has_recommendation(self, validator, mock_site, tmp_path):
        """Structure warning has recommendation."""
        bad_html = "<html><body></body></html>"  # No DOCTYPE
        page = create_page(mock_site.output_dir, "bad.html", bad_html)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        structure_warning = next(
            (r for r in warning_results if "structure" in r.message.lower()), None
        )
        if structure_warning:
            assert structure_warning.recommendation is not None

    def test_seo_warning_has_recommendation(self, validator, mock_site, tmp_path):
        """SEO warning has recommendation."""
        no_seo = "<!DOCTYPE html><html><head></head><body></body></html>"
        page = create_page(mock_site.output_dir, "no-seo.html", no_seo)
        mock_site.pages = [page]

        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        seo_warning = next((r for r in warning_results if "seo" in r.message.lower()), None)
        if seo_warning:
            assert seo_warning.recommendation is not None
