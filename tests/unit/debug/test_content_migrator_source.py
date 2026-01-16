"""
Unit tests for ContentMigrator source attribute usage.

Verifies that ContentMigrator uses page._source (raw markdown) instead of
page.content (rendered HTML) when detecting links and patterns.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.debug import ContentMigrator


class TestContentMigratorLinkDetection:
    """ContentMigrator must use _source (markdown) not content (HTML)."""

    @pytest.fixture
    def mock_site_with_pages(self) -> MagicMock:
        """Create mock site with pages having different _source and content."""
        site = MagicMock()
        site.root_path = Path("/fake/root")
        
        # Create mock page where _source (markdown) != content (HTML)
        mock_page = MagicMock()
        mock_page._source = "Check [this link](/docs/guide) for more info."
        mock_page.content = "<p>Check <a href='/docs/guide'>this link</a> for more info.</p>"
        mock_page.source_path = Path("content/index.md")
        mock_page.href = "/index/"
        
        site.pages = [mock_page]
        return site

    def test_finds_links_in_markdown_source(self, mock_site_with_pages: MagicMock) -> None:
        """Link detection must work on raw markdown, not rendered HTML.
        
        This test would have failed if ContentMigrator used page.content
        (HTML) instead of page._source (markdown), because the regex
        pattern `\\[...\\]\\(...\\)` won't match HTML anchor tags.
        """
        migrator = ContentMigrator(site=mock_site_with_pages)
        preview = migrator.preview_move("docs/guide.md", "tutorials/guide.md")

        # Should find the link in markdown format
        assert len(preview.affected_links) == 1
        assert preview.affected_links[0].old_link == "/docs/guide"

    def test_link_detection_ignores_html_anchors(self) -> None:
        """Verify HTML anchor tags are not detected (we want markdown links)."""
        site = MagicMock()
        site.root_path = Path("/fake/root")
        
        # Page with HTML anchor but NO markdown link
        mock_page = MagicMock()
        mock_page._source = "Just text with no markdown links."  # No markdown link
        mock_page.content = "<p>Check <a href='/docs/guide'>this</a></p>"  # Has HTML link
        mock_page.source_path = Path("content/page.md")
        
        site.pages = [mock_page]
        
        migrator = ContentMigrator(site=site)
        preview = migrator.preview_move("docs/guide.md", "new/guide.md")

        # Should NOT find the HTML link (we're searching markdown, not HTML)
        assert len(preview.affected_links) == 0


class TestContentMigratorLargePageDetection:
    """ContentMigrator must count lines from markdown, not HTML."""

    def test_counts_lines_from_markdown_not_html(self) -> None:
        """Large page detection must count markdown lines, not HTML lines.
        
        HTML rendering often collapses many markdown lines into fewer HTML
        lines (or vice versa). Line counting should use the source markdown.
        """
        site = MagicMock()
        site.root_path = Path("/fake/root")
        
        # Create page with many markdown lines but few HTML lines
        mock_page = MagicMock()
        mock_page._source = "\n".join(["line"] * 600)  # 600 lines of markdown
        mock_page.content = "<p>" + "</p><p>".join(["line"] * 600) + "</p>"  # Compact HTML
        mock_page.source_path = Path("content/big-page.md")
        mock_page.href = "/big-page/"
        
        site.pages = [mock_page]
        
        migrator = ContentMigrator(site=site)
        findings = migrator._find_structure_issues()

        # Should detect as large (>500 lines in markdown source)
        large_findings = [f for f in findings if "large" in f.title.lower()]
        assert len(large_findings) == 1, "Should detect page with 600 markdown lines as large"

    def test_small_markdown_not_detected_as_large(self) -> None:
        """Pages with few markdown lines should not be flagged as large."""
        site = MagicMock()
        site.root_path = Path("/fake/root")
        
        # Create page with few markdown lines
        mock_page = MagicMock()
        mock_page._source = "\n".join(["line"] * 100)  # Only 100 lines
        mock_page.content = "<p>..." + "x" * 10000 + "...</p>"  # Large HTML (shouldn't matter)
        mock_page.source_path = Path("content/small-page.md")
        mock_page.href = "/small-page/"
        
        site.pages = [mock_page]
        
        migrator = ContentMigrator(site=site)
        findings = migrator._find_structure_issues()

        # Should NOT detect as large (only 100 markdown lines)
        large_findings = [f for f in findings if "large" in f.title.lower()]
        assert len(large_findings) == 0, "Page with 100 lines should not be flagged as large"


class TestContentMigratorOrphanDetection:
    """ContentMigrator must find orphan pages using markdown links."""

    def test_orphan_detection_uses_markdown_source(self) -> None:
        """Orphan page detection must scan markdown links, not HTML."""
        site = MagicMock()
        site.root_path = Path("/fake/root")
        
        # Page A links to Page B in markdown
        page_a = MagicMock()
        page_a._source = "See [Page B](/page-b/) for details."
        page_a.content = "<p>See <a href='/page-b/'>Page B</a> for details.</p>"
        page_a.source_path = Path("content/page-a.md")
        page_a.href = "/page-a/"
        
        # Page B (linked from A, should NOT be orphan)
        page_b = MagicMock()
        page_b._source = "This is Page B."
        page_b.content = "<p>This is Page B.</p>"
        page_b.source_path = Path("content/page-b.md")
        page_b.href = "/page-b/"
        
        # Page C (NOT linked, should be orphan)
        page_c = MagicMock()
        page_c._source = "This is Page C, nobody links here."
        page_c.content = "<p>This is Page C, nobody links here.</p>"
        page_c.source_path = Path("content/page-c.md")
        page_c.href = "/page-c/"
        
        site.pages = [page_a, page_b, page_c]
        
        migrator = ContentMigrator(site=site)
        findings = migrator._find_structure_issues()

        # Find orphan-related findings
        orphan_findings = [f for f in findings if "orphan" in f.title.lower()]
        
        # Page C should be detected as orphan (no incoming links)
        # Page A and Page B should not be orphans
        if orphan_findings:
            orphans = orphan_findings[0].metadata.get("orphans", [])
            # page-c should be in orphans (no one links to it)
            # page-b should NOT be in orphans (page-a links to it)
            page_c_paths = [p for p in orphans if "page-c" in p]
            page_b_paths = [p for p in orphans if "page-b" in p]
            
            assert len(page_b_paths) == 0, "page-b has incoming link, should not be orphan"


class TestContentMigratorPreviewLineNumbers:
    """Test that line numbers are calculated from markdown source."""

    def test_line_number_calculation_uses_source(self) -> None:
        """Line numbers in affected_links should be from markdown source."""
        site = MagicMock()
        site.root_path = Path("/fake/root")
        
        # Create page with link on specific line
        markdown_content = """# Title

Some intro text.

Here is [a link](/target/) in the middle.

More text below.
"""
        mock_page = MagicMock()
        mock_page._source = markdown_content
        mock_page.content = "<h1>Title</h1><p>Some intro text.</p>..."  # Different structure
        mock_page.source_path = Path("content/test.md")
        
        site.pages = [mock_page]
        
        migrator = ContentMigrator(site=site)
        preview = migrator.preview_move("target/index.md", "new-target/index.md")

        if preview.affected_links:
            # Line number should be 5 (counting from markdown source)
            # The link appears after: line 1 (# Title), 2 (empty), 3 (intro), 4 (empty), 5 (link)
            assert preview.affected_links[0].line == 5
