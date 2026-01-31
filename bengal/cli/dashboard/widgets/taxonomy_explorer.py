"""
Taxonomy Explorer Widget.

Hierarchical drill-down view for site taxonomies.
Shows tags, categories, and other taxonomies with term counts.

Usage:
    from bengal.cli.dashboard.widgets import TaxonomyExplorer

    explorer = TaxonomyExplorer()
    explorer.set_site(site)

RFC: rfc-dashboard-api-integration
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static, Tree

if TYPE_CHECKING:
    from bengal.core.site import Site


class TaxonomyExplorer(Vertical):
    """
    Tree browser for site taxonomies.

    Displays hierarchical view of:
    - Taxonomies (tags, categories, etc.) as root nodes
    - Terms under each taxonomy
    - Page count per term

    Features:
    - Expandable taxonomy groups
    - Term page counts
    - Quick navigation to term pages

    Example:
        explorer = TaxonomyExplorer(id="taxonomy-explorer")
        explorer.set_site(site)

    """

    DEFAULT_CSS = """
    TaxonomyExplorer {
        height: 100%;
        border: solid $primary;
        padding: 0 1;
    }
    TaxonomyExplorer .explorer-header {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    TaxonomyExplorer Tree {
        height: 1fr;
    }
    """

    taxonomy_count: reactive[int] = reactive(0)
    term_count: reactive[int] = reactive(0)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize taxonomy explorer."""
        super().__init__(id=id, classes=classes)
        self._site: Site | None = None
        self._tree: Tree | None = None

    def compose(self) -> ComposeResult:
        """Compose the taxonomy explorer."""
        yield Static(
            self._format_header(),
            classes="explorer-header",
            id="taxonomy-header",
        )
        self._tree = Tree("Taxonomies", id="taxonomy-tree")
        self._tree.root.expand()
        yield self._tree

    def set_site(self, site: Site) -> None:
        """
        Populate the tree from a Site object.

        Args:
            site: Site instance with taxonomies
        """
        self._site = site
        self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        """Rebuild the tree from current site data."""
        if self._tree is None or self._site is None:
            return

        # Clear existing tree
        self._tree.root.remove_children()

        # Get taxonomies from site
        taxonomies = getattr(self._site, "taxonomies", {})
        if not taxonomies:
            self._tree.root.add_leaf("No taxonomies configured")
            self.taxonomy_count = 0
            self.term_count = 0
            self._update_header()
            return

        total_terms = 0

        # Add each taxonomy as a parent node
        for tax_name in sorted(taxonomies.keys()):
            tax_data = taxonomies[tax_name]
            terms = tax_data.get("terms", {}) if isinstance(tax_data, dict) else {}

            # Icon based on taxonomy type
            icon = self._get_taxonomy_icon(tax_name)
            term_count = len(terms)
            total_terms += term_count

            tax_label = f"{icon} {tax_name.title()} ({term_count})"
            tax_node = self._tree.root.add(
                tax_label,
                data={"type": "taxonomy", "name": tax_name},
            )

            # Add terms under taxonomy
            for term_name in sorted(terms.keys()):
                term_pages = terms[term_name]
                page_count = len(term_pages) if isinstance(term_pages, list) else 0
                term_label = f"🏷️ {term_name} ({page_count} pages)"
                tax_node.add_leaf(
                    term_label,
                    data={
                        "type": "term",
                        "taxonomy": tax_name,
                        "term": term_name,
                        "pages": term_pages,
                    },
                )

        # Update counts
        self.taxonomy_count = len(taxonomies)
        self.term_count = total_terms
        self._update_header()

    def _get_taxonomy_icon(self, name: str) -> str:
        """Get icon for taxonomy type."""
        icons = {
            "tags": "🏷️",
            "categories": "📁",
            "authors": "👤",
            "series": "📚",
            "topics": "💡",
        }
        return icons.get(name.lower(), "📋")

    def _format_header(self) -> str:
        """Format header with counts."""
        return f"🏷️ Taxonomies ({self.taxonomy_count} types, {self.term_count} terms)"

    def _update_header(self) -> None:
        """Update the header widget."""
        try:
            header = self.query_one("#taxonomy-header", Static)
            header.update(self._format_header())
        except Exception:
            pass  # Widget may not be mounted yet during compose

    def refresh_from_site(self) -> None:
        """Refresh data from current site."""
        if self._site is not None:
            self._rebuild_tree()
