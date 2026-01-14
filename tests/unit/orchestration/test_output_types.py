"""
Tests for output type classification.

RFC: Output Cache Architecture - Tests OutputType enum and classify_output()
function for categorizing outputs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.orchestration.build.output_types import (
    OutputType,
    classify_output,
    is_aggregate_output,
    is_content_output,
)


class TestOutputType:
    """Tests for OutputType enum."""

    def test_all_types_defined(self) -> None:
        """All expected output types exist."""
        assert OutputType.CONTENT_PAGE
        assert OutputType.GENERATED_PAGE
        assert OutputType.AGGREGATE_INDEX
        assert OutputType.AGGREGATE_FEED
        assert OutputType.AGGREGATE_TEXT
        assert OutputType.ASSET
        assert OutputType.STATIC


class TestClassifyOutput:
    """Tests for classify_output function."""

    # Aggregate files
    def test_sitemap_is_aggregate_feed(self) -> None:
        """sitemap.xml is classified as AGGREGATE_FEED."""
        path = Path("public/sitemap.xml")
        assert classify_output(path) == OutputType.AGGREGATE_FEED

    def test_rss_is_aggregate_feed(self) -> None:
        """rss.xml is classified as AGGREGATE_FEED."""
        path = Path("public/rss.xml")
        assert classify_output(path) == OutputType.AGGREGATE_FEED

    def test_atom_is_aggregate_feed(self) -> None:
        """atom.xml is classified as AGGREGATE_FEED."""
        path = Path("public/atom.xml")
        assert classify_output(path) == OutputType.AGGREGATE_FEED

    def test_index_json_is_aggregate_index(self) -> None:
        """index.json is classified as AGGREGATE_INDEX."""
        path = Path("public/index.json")
        assert classify_output(path) == OutputType.AGGREGATE_INDEX

    def test_llm_full_is_aggregate_text(self) -> None:
        """llm-full.txt is classified as AGGREGATE_TEXT."""
        path = Path("public/llm-full.txt")
        assert classify_output(path) == OutputType.AGGREGATE_TEXT

    # Content pages
    def test_html_is_content_page(self) -> None:
        """HTML files are classified as CONTENT_PAGE."""
        path = Path("public/docs/index.html")
        assert classify_output(path) == OutputType.CONTENT_PAGE

    def test_generated_page_with_metadata(self) -> None:
        """HTML with _generated metadata is GENERATED_PAGE."""
        path = Path("public/tags/python/index.html")
        metadata = {"_generated": True}
        assert classify_output(path, metadata) == OutputType.GENERATED_PAGE

    # Assets
    def test_css_is_asset(self) -> None:
        """CSS files are classified as ASSET."""
        path = Path("public/assets/style.css")
        assert classify_output(path) == OutputType.ASSET

    def test_js_is_asset(self) -> None:
        """JS files are classified as ASSET."""
        path = Path("public/assets/main.js")
        assert classify_output(path) == OutputType.ASSET

    def test_css_outside_assets_is_asset(self) -> None:
        """CSS files outside assets/ are still ASSET."""
        path = Path("public/custom/style.css")
        assert classify_output(path) == OutputType.ASSET

    def test_image_is_asset(self) -> None:
        """Image files are classified as ASSET."""
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]:
            path = Path(f"public/images/logo{ext}")
            assert classify_output(path) == OutputType.ASSET

    def test_font_is_asset(self) -> None:
        """Font files are classified as ASSET."""
        for ext in [".woff", ".woff2", ".ttf", ".eot", ".otf"]:
            path = Path(f"public/fonts/inter{ext}")
            assert classify_output(path) == OutputType.ASSET

    # Static files
    def test_favicon_is_static(self) -> None:
        """favicon.ico is classified as STATIC."""
        path = Path("public/favicon.ico")
        assert classify_output(path) == OutputType.STATIC

    def test_robots_txt_is_static(self) -> None:
        """robots.txt is classified as STATIC."""
        path = Path("public/robots.txt")
        assert classify_output(path) == OutputType.STATIC

    def test_cname_is_static(self) -> None:
        """CNAME is classified as STATIC."""
        path = Path("public/CNAME")
        assert classify_output(path) == OutputType.STATIC

    def test_unknown_file_is_static(self) -> None:
        """Unknown file types default to STATIC."""
        path = Path("public/random.dat")
        assert classify_output(path) == OutputType.STATIC


class TestIsAggregateOutput:
    """Tests for is_aggregate_output helper."""

    def test_aggregate_index_is_aggregate(self) -> None:
        """AGGREGATE_INDEX is aggregate."""
        assert is_aggregate_output(OutputType.AGGREGATE_INDEX) is True

    def test_aggregate_feed_is_aggregate(self) -> None:
        """AGGREGATE_FEED is aggregate."""
        assert is_aggregate_output(OutputType.AGGREGATE_FEED) is True

    def test_aggregate_text_is_aggregate(self) -> None:
        """AGGREGATE_TEXT is aggregate."""
        assert is_aggregate_output(OutputType.AGGREGATE_TEXT) is True

    def test_content_page_not_aggregate(self) -> None:
        """CONTENT_PAGE is not aggregate."""
        assert is_aggregate_output(OutputType.CONTENT_PAGE) is False

    def test_asset_not_aggregate(self) -> None:
        """ASSET is not aggregate."""
        assert is_aggregate_output(OutputType.ASSET) is False


class TestIsContentOutput:
    """Tests for is_content_output helper."""

    def test_content_page_is_content(self) -> None:
        """CONTENT_PAGE is content."""
        assert is_content_output(OutputType.CONTENT_PAGE) is True

    def test_generated_page_is_content(self) -> None:
        """GENERATED_PAGE is content."""
        assert is_content_output(OutputType.GENERATED_PAGE) is True

    def test_aggregate_not_content(self) -> None:
        """Aggregate types are not content."""
        assert is_content_output(OutputType.AGGREGATE_INDEX) is False
        assert is_content_output(OutputType.AGGREGATE_FEED) is False

    def test_asset_not_content(self) -> None:
        """ASSET is not content."""
        assert is_content_output(OutputType.ASSET) is False

    def test_static_not_content(self) -> None:
        """STATIC is not content."""
        assert is_content_output(OutputType.STATIC) is False
