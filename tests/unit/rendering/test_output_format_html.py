"""
Tests for format_html function in rendering pipeline output.

RFC: rfc-build-performance-optimizations - Tests fast_mode skipping formatting.
"""

from __future__ import annotations

from pathlib import Path

from bengal.core.page import Page
from bengal.core.site import Site
from bengal.rendering.pipeline.output import format_html


class TestFormatHtmlFastMode:
    """Tests for fast_mode skipping HTML formatting."""

    def test_fast_mode_skips_formatting(self) -> None:
        """fast_mode=True should return raw HTML without formatting."""
        html = "<div>  \n  Hello  \n  </div>"
        
        # Create a minimal site with fast_mode enabled
        site = Site(
            root_path=Path("/tmp/test"),
            output_dir=Path("/tmp/test/output"),
            config={"build": {"fast_mode": True}},
        )
        page = Page(source_path=Path("/tmp/test/page.md"))
        
        result = format_html(html, page, site)
        
        # Should return unchanged HTML (no formatting applied)
        assert result == html

    def test_fast_mode_still_embeds_content_hash(self) -> None:
        """fast_mode should still embed content hash if enabled."""
        html = "<html><head></head><body>Test</body></html>"
        
        site = Site(
            root_path=Path("/tmp/test"),
            output_dir=Path("/tmp/test/output"),
            config={
                "build": {
                    "fast_mode": True,
                    "content_hash_in_html": True,
                }
            },
        )
        page = Page(source_path=Path("/tmp/test/page.md"))
        
        result = format_html(html, page, site)
        
        # Should have content hash embedded
        assert 'name="bengal:content-hash"' in result
        # But HTML should otherwise be unchanged (no pretty-printing)
        assert "<head>" in result  # Not formatted

    def test_fast_mode_false_applies_formatting(self) -> None:
        """fast_mode=False should apply formatting as normal."""
        html = "<div>  \n  Hello  \n  </div>"
        
        site = Site(
            root_path=Path("/tmp/test"),
            output_dir=Path("/tmp/test/output"),
            config={
                "build": {"fast_mode": False},
                "html_output": {"mode": "pretty"},
            },
        )
        page = Page(source_path=Path("/tmp/test/page.md"))
        
        result = format_html(html, page, site)
        
        # Should be formatted (pretty mode)
        # The exact formatting depends on format_html_output, but it should differ from input
        assert result != html or "  \n  " not in result

    def test_fast_mode_overrides_page_no_format(self) -> None:
        """fast_mode should take precedence over page.metadata.no_format."""
        html = "<div>  \n  Hello  \n  </div>"
        
        site = Site(
            root_path=Path("/tmp/test"),
            output_dir=Path("/tmp/test/output"),
            config={
                "build": {"fast_mode": True},
                "html_output": {"mode": "pretty"},
            },
        )
        page = Page(source_path=Path("/tmp/test/page.md"))
        page.metadata["no_format"] = False  # Would normally format
        
        result = format_html(html, page, site)
        
        # fast_mode should win - no formatting
        assert result == html

    def test_fast_mode_overrides_html_output_mode(self) -> None:
        """fast_mode should take precedence over html_output.mode."""
        html = "<div>  \n  Hello  \n  </div>"
        
        site = Site(
            root_path=Path("/tmp/test"),
            output_dir=Path("/tmp/test/output"),
            config={
                "build": {"fast_mode": True},
                "html_output": {"mode": "minify"},  # Would normally minify
            },
        )
        page = Page(source_path=Path("/tmp/test/page.md"))
        
        result = format_html(html, page, site)
        
        # fast_mode should win - no formatting
        assert result == html
