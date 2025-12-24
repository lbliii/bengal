"""Integration tests for gallery directive.

Tests gallery directive functionality:
- Grid rendering with CSS classes
- Image parsing from markdown
- Lightbox attribute
- Custom column options

Phase 2 of RFC: User Scenario Coverage - Extended Validation
"""

from __future__ import annotations

import pytest


@pytest.mark.bengal(testroot="test-gallery")
class TestGalleryDirective:
    """Test gallery directive rendering."""

    def test_gallery_page_exists(self, site) -> None:
        """Gallery test page should be discovered."""
        gallery_pages = [p for p in site.pages if "gallery" in str(p.source_path).lower()]
        assert len(gallery_pages) >= 1, "Should have at least 1 gallery page"

    def test_gallery_builds_successfully(self, site, build_site) -> None:
        """Site with gallery directive should build without errors."""
        build_site()

        output = site.output_dir
        assert (output / "gallery" / "index.html").exists(), "Gallery page should be generated"

    def test_gallery_renders_grid(self, site, build_site) -> None:
        """Gallery should render with CSS grid class."""
        build_site()

        html = (site.output_dir / "gallery" / "index.html").read_text()

        # Should have gallery container class
        assert 'class="gallery' in html, "Gallery should have gallery class"

    def test_gallery_parses_images(self, site, build_site) -> None:
        """Gallery should parse markdown images and render them."""
        build_site()

        html = (site.output_dir / "gallery" / "index.html").read_text()

        # Should have gallery items
        assert "gallery__item" in html, "Gallery should render gallery__item elements"

        # Should have images
        assert "<img" in html, "Gallery should render images"

    def test_gallery_lightbox_attribute(self, site, build_site) -> None:
        """Gallery should include lightbox data attribute."""
        build_site()

        html = (site.output_dir / "gallery" / "index.html").read_text()

        # Should have data-lightbox attribute
        assert 'data-lightbox="true"' in html or 'data-lightbox="false"' in html, (
            "Gallery should have data-lightbox attribute"
        )

    def test_gallery_custom_columns(self, site, build_site) -> None:
        """Gallery should support custom column options."""
        build_site()

        html = (site.output_dir / "gallery" / "index.html").read_text()

        # Should have custom column CSS variable
        assert "--gallery-columns" in html, "Gallery should use --gallery-columns CSS variable"


class TestGalleryDirectiveUnit:
    """Unit tests for gallery directive parsing."""

    def test_image_pattern_matches_basic(self) -> None:
        """Image pattern should match basic markdown images."""
        from bengal.directives.gallery import IMAGE_PATTERN

        content = "![Alt text](/images/photo.jpg)"
        matches = list(IMAGE_PATTERN.finditer(content))

        assert len(matches) == 1
        assert matches[0].group(1) == "Alt text"
        assert matches[0].group(2) == "/images/photo.jpg"

    def test_image_pattern_matches_with_title(self) -> None:
        """Image pattern should match images with title."""
        from bengal.directives.gallery import IMAGE_PATTERN

        content = '![Alt text](/images/photo.jpg "Photo title")'
        matches = list(IMAGE_PATTERN.finditer(content))

        assert len(matches) == 1
        assert matches[0].group(1) == "Alt text"
        assert matches[0].group(2) == "/images/photo.jpg"
        assert matches[0].group(3) == "Photo title"

    def test_image_pattern_matches_multiple(self) -> None:
        """Image pattern should match multiple images."""
        from bengal.directives.gallery import IMAGE_PATTERN

        content = """
![Photo 1](/images/photo1.jpg)
![Photo 2](/images/photo2.jpg "Second photo")
![Photo 3](/images/photo3.jpg)
"""
        matches = list(IMAGE_PATTERN.finditer(content))

        assert len(matches) == 3

    def test_gallery_options_defaults(self) -> None:
        """Gallery options should have sensible defaults."""
        from bengal.directives.gallery import GalleryOptions

        options = GalleryOptions.from_raw({})

        assert options.columns == 3
        assert options.lightbox is True
        assert options.gap == "1rem"
        assert options.aspect_ratio == "4/3"

    def test_gallery_options_custom(self) -> None:
        """Gallery options should parse custom values."""
        from bengal.directives.gallery import GalleryOptions

        options = GalleryOptions.from_raw(
            {
                "columns": "4",
                "lightbox": "false",
                "gap": "0.5rem",
                "class": "custom-gallery",
            }
        )

        assert options.columns == 4
        assert options.lightbox is False
        assert options.gap == "0.5rem"
        assert options.css_class == "custom-gallery"

    def test_gallery_directive_registered(self) -> None:
        """Gallery directive should be registered."""
        from bengal.directives.registry import KNOWN_DIRECTIVE_NAMES

        assert "gallery" in KNOWN_DIRECTIVE_NAMES, (
            "gallery should be registered in directive registry"
        )


class TestGalleryCSS:
    """Test gallery CSS exists and has expected content."""

    def test_gallery_css_exists(self) -> None:
        """Gallery CSS file should exist."""
        from pathlib import Path

        themes_dir = Path(__file__).parent.parent.parent / "bengal" / "themes" / "default"
        css_path = themes_dir / "assets" / "css" / "components" / "gallery.css"

        assert css_path.exists(), f"Gallery CSS should exist at {css_path}"

    def test_gallery_css_content(self) -> None:
        """Gallery CSS should contain expected selectors."""
        from pathlib import Path

        themes_dir = Path(__file__).parent.parent.parent / "bengal" / "themes" / "default"
        css_path = themes_dir / "assets" / "css" / "components" / "gallery.css"

        content = css_path.read_text()

        # Check for key selectors
        assert ".gallery" in content, "Should have .gallery selector"
        assert ".gallery__item" in content, "Should have .gallery__item selector"
        assert ".gallery__image" in content, "Should have .gallery__image selector"
        assert ".gallery__caption" in content, "Should have .gallery__caption selector"
        assert "--gallery-columns" in content, "Should use CSS custom properties"


