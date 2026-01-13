"""
Content Browser Widget.

Tree view for browsing site pages and sections.
Inspired by file browser patterns from IDE editors.

Usage:
    from bengal.cli.dashboard.widgets import ContentBrowser

    browser = ContentBrowser()
    browser.set_site(site)  # Populates tree from Site object

RFC: rfc-dashboard-api-integration
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static, Tree

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site


class ContentBrowser(Vertical):
    """
    Tree browser for site content (pages and sections).
    
    Displays hierarchical view of:
    - Sections as expandable folders
    - Pages as leaf nodes with metadata preview
    
    Features:
    - Lazy loading for large sites
    - Section/page counts in node labels
    - Selection callback for page details
    
    Example:
        browser = ContentBrowser(id="content-browser")
        browser.set_site(site)
    
        @browser.on_select
        def show_page_details(page: Page):
            details.update(page)
        
    """

    DEFAULT_CSS = """
    ContentBrowser {
        height: 100%;
        border: solid $primary;
        padding: 0 1;
    }
    ContentBrowser .browser-header {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    ContentBrowser Tree {
        height: 1fr;
    }
    ContentBrowser .page-node {
        color: $text;
    }
    ContentBrowser .section-node {
        color: $primary;
    }
    ContentBrowser .draft-page {
        color: $text-muted;
    }
    """

    page_count: reactive[int] = reactive(0)
    section_count: reactive[int] = reactive(0)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize content browser."""
        super().__init__(id=id, classes=classes)
        self._site: Site | None = None
        self._tree: Tree | None = None

    def compose(self) -> ComposeResult:
        """Compose the content browser."""
        yield Static(
            f"📄 Content ({self.page_count} pages, {self.section_count} sections)",
            classes="browser-header",
            id="content-header",
        )
        self._tree = Tree("Site", id="content-tree")
        self._tree.root.expand()
        yield self._tree

    def set_site(self, site: Site) -> None:
        """
        Populate the tree from a Site object.

        Args:
            site: Site instance with pages and sections
        """
        self._site = site
        self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        """Rebuild the tree from current site data."""
        if self._tree is None or self._site is None:
            return

        # Clear existing tree
        self._tree.root.remove_children()

        # Build section -> pages mapping
        section_pages: dict[str, list[Page]] = {}
        orphan_pages: list[Page] = []

        for page in self._site.pages:
            section_path = page.section_path or ""
            if section_path:
                if section_path not in section_pages:
                    section_pages[section_path] = []
                section_pages[section_path].append(page)
            else:
                orphan_pages.append(page)

        # Add sections with their pages
        for section in sorted(self._site.sections, key=lambda s: str(s.source_path)):
            section_path = str(section.source_path)
            pages = section_pages.get(section_path, [])
            page_count = len(pages)

            # Add section node
            section_label = f"📁 {section.title or section.name} ({page_count})"
            section_node = self._tree.root.add(
                section_label,
                data={"type": "section", "section": section},
            )

            # Add pages under section
            for page in sorted(pages, key=lambda p: p.title or ""):
                page_label = self._format_page_label(page)
                section_node.add_leaf(
                    page_label,
                    data={"type": "page", "page": page},
                )

        # Add orphan pages at root level
        if orphan_pages:
            for page in sorted(orphan_pages, key=lambda p: p.title or ""):
                page_label = self._format_page_label(page)
                self._tree.root.add_leaf(
                    page_label,
                    data={"type": "page", "page": page},
                )

        # Update counts
        self.page_count = len(self._site.pages)
        self.section_count = len(self._site.sections)

        # Update header
        header = self.query_one("#content-header", Static)
        header.update(f"📄 Content ({self.page_count} pages, {self.section_count} sections)")

    def _format_page_label(self, page: Page) -> str:
        """Format page label with status indicators."""
        title = page.title or page.slug or "Untitled"
        metadata = page.metadata or {}

        # Status indicators
        indicators = []
        if metadata.get("draft"):
            indicators.append("📝")
        if metadata.get("_generated"):
            indicators.append("⚡")
        if page.template == "archive.html":
            indicators.append("📚")

        indicator_str = " ".join(indicators)
        if indicator_str:
            return f"{indicator_str} {title}"
        return f"📄 {title}"

    def refresh_from_site(self) -> None:
        """Refresh tree data from current site."""
        if self._site is not None:
            self._rebuild_tree()
