"""
Graph building logic for Knowledge Graph.

This module handles the construction of the knowledge graph by analyzing
various connection types between pages: cross-references, taxonomies,
related posts, menu items, section hierarchy, and navigation links.

Extracted from knowledge_graph.py per RFC: rfc-modularize-large-files.

Classes:
    GraphBuilder: Builds the knowledge graph from site data.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from bengal.analysis.link_types import LinkMetrics, LinkType
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


class GraphBuilder:
    """
    Builds the knowledge graph by analyzing page connections.

    Analyzes connections from multiple sources:
    - Cross-references: Internal markdown links between pages
    - Taxonomies: Shared tags and categories
    - Related posts: Algorithm-computed relationships
    - Menu items: Navigation structure
    - Section hierarchy: Parent-child relationships
    - Navigation links: Next/prev sequential relationships

    Attributes:
        site: Site instance to analyze
        exclude_autodoc: Whether to exclude autodoc pages from analysis
        incoming_refs: Dict mapping pages to incoming reference counts
        outgoing_refs: Dict mapping pages to sets of target pages
        link_types: Dict mapping (source, target) tuples to link types
        link_metrics: Dict mapping pages to LinkMetrics objects

    Example:
        >>> builder = GraphBuilder(site, exclude_autodoc=True)
        >>> builder.build()
        >>> # Results available in builder.incoming_refs, etc.
    """

    def __init__(
        self,
        site: Site,
        exclude_autodoc: bool = True,
    ):
        """
        Initialize the graph builder.

        Args:
            site: Site instance to analyze
            exclude_autodoc: If True, exclude autodoc/API reference pages
        """
        self.site = site
        self.exclude_autodoc = exclude_autodoc

        # Graph data structures
        self.incoming_refs: dict[Page, float] = defaultdict(float)
        self.outgoing_refs: dict[Page, set[Page]] = defaultdict(set)
        self.link_types: dict[tuple[Page | None, Page], LinkType] = {}
        self.link_metrics: dict[Page, LinkMetrics] = {}

    def get_analysis_pages(self) -> list[Page]:
        """
        Get list of pages to analyze, excluding autodoc pages if configured.

        Returns:
            List of pages to include in graph analysis
        """
        from bengal.utils.autodoc import is_autodoc_page

        if not self.exclude_autodoc:
            return list(self.site.pages)

        return [p for p in self.site.pages if not is_autodoc_page(p)]

    def build(self) -> None:
        """
        Build the knowledge graph by analyzing all page connections.

        Analyzes:
        1. Cross-references (internal links between pages)
        2. Taxonomy references (pages grouped by tags/categories)
        3. Related posts (pre-computed relationships)
        4. Menu items (navigation references)
        5. Section hierarchy (parent-child relationships)
        6. Navigation links (next/prev sequential relationships)
        """
        # Ensure links are extracted from pages
        self._ensure_links_extracted()

        # Count references from different sources
        self._analyze_cross_references()
        self._analyze_taxonomies()
        self._analyze_related_posts()
        self._analyze_menus()

        # Semantic link analysis - track structural relationships
        self._analyze_section_hierarchy()
        self._analyze_navigation_links()

        # Build link metrics for each page
        self._build_link_metrics()

    def _ensure_links_extracted(self) -> None:
        """
        Extract links from all pages if not already extracted.

        Links are normally extracted during rendering, but graph analysis
        needs them before rendering happens. This ensures links are available.
        """
        analysis_pages = self.get_analysis_pages()
        for page in analysis_pages:
            if not hasattr(page, "links") or not page.links:
                try:
                    page.extract_links()
                except (AttributeError, TypeError) as e:
                    logger.warning(
                        "knowledge_graph_link_extraction_error",
                        page=str(page.source_path),
                        error=str(e),
                        type=type(e).__name__,
                    )
                except Exception as e:
                    logger.debug(
                        "knowledge_graph_link_extraction_failed",
                        page=str(page.source_path),
                        error=str(e),
                        exc_info=True,
                    )

    def _analyze_cross_references(self) -> None:
        """
        Analyze cross-references (internal links between pages).

        Uses the site's xref_index to find all internal links.
        Only analyzes links from/to pages included in analysis (excludes autodoc).
        """
        if not hasattr(self.site, "xref_index") or not self.site.xref_index:
            logger.debug("knowledge_graph_no_xref_index", action="skipping cross-ref analysis")
            return

        analysis_pages = self.get_analysis_pages()
        analysis_pages_set = set(analysis_pages)

        for page in analysis_pages:
            for link in getattr(page, "links", []):
                target = self._resolve_link(link)
                if target and target != page and target in analysis_pages_set:
                    self.incoming_refs[target] += 1
                    self.outgoing_refs[page].add(target)
                    self.link_types[(page, target)] = LinkType.EXPLICIT

    def _resolve_link(self, link: str) -> Page | None:
        """
        Resolve a link string to a target page.

        Args:
            link: Link string (path, slug, or ID)

        Returns:
            Target page or None if not found
        """
        if not hasattr(self.site, "xref_index") or not self.site.xref_index:
            return None

        xref = self.site.xref_index

        # Try by ID
        if link.startswith("id:"):
            page = xref.get("by_id", {}).get(link[3:])
            return page if page is not None else None

        # Try by path
        if "/" in link or link.endswith(".md"):
            clean_link = link.replace(".md", "").strip("/")
            page = xref.get("by_path", {}).get(clean_link)
            return page if page is not None else None

        # Try by slug
        pages = xref.get("by_slug", {}).get(link, [])
        return pages[0] if pages else None

    def _analyze_taxonomies(self) -> None:
        """
        Analyze taxonomy references (pages grouped by tags/categories).

        Pages in the same taxonomy group reference each other implicitly.
        Only includes pages in analysis (excludes autodoc).
        """
        if not hasattr(self.site, "taxonomies") or not self.site.taxonomies:
            logger.debug("knowledge_graph_no_taxonomies", action="skipping taxonomy analysis")
            return

        analysis_pages_set = set(self.get_analysis_pages())

        for _taxonomy_name, taxonomy_dict in self.site.taxonomies.items():
            for _term_slug, term_data in taxonomy_dict.items():
                pages = term_data.get("pages", [])
                for page in pages:
                    if page in analysis_pages_set:
                        self.incoming_refs[page] += 1
                        self.link_types[(None, page)] = LinkType.TAXONOMY

    def _analyze_related_posts(self) -> None:
        """
        Analyze related posts (pre-computed relationships).

        Related posts are pages that share tags or other criteria.
        Only includes pages in analysis (excludes autodoc).
        """
        analysis_pages = self.get_analysis_pages()
        analysis_pages_set = set(analysis_pages)

        for page in analysis_pages:
            if not hasattr(page, "related_posts") or not page.related_posts:
                continue

            for related in page.related_posts:
                if related != page and related in analysis_pages_set:
                    self.incoming_refs[related] += 1
                    self.outgoing_refs[page].add(related)
                    self.link_types[(page, related)] = LinkType.RELATED

    def _analyze_menus(self) -> None:
        """
        Analyze menu items (navigation references).

        Pages in menus get a significant boost in importance.
        Only includes pages in analysis (excludes autodoc).
        """
        if not hasattr(self.site, "menu") or not self.site.menu:
            logger.debug("knowledge_graph_no_menus", action="skipping menu analysis")
            return

        analysis_pages_set = set(self.get_analysis_pages())

        for _menu_name, menu_items in self.site.menu.items():
            for item in menu_items:
                if hasattr(item, "page") and item.page and item.page in analysis_pages_set:
                    self.incoming_refs[item.page] += 10
                    self.link_types[(None, item.page)] = LinkType.MENU

    def _analyze_section_hierarchy(self) -> None:
        """
        Analyze implicit section links (parent _index.md → children).

        Section index pages implicitly link to all child pages in their
        directory. This represents topical containment—the parent page
        defines the topic, children belong to that topic.

        Weight: 0.5 (structural but semantically meaningful)
        """
        analysis_pages = self.get_analysis_pages()
        analysis_pages_set = set(analysis_pages)

        for page in analysis_pages:
            is_index = hasattr(page, "source_path") and page.source_path.stem in (
                "_index",
                "index",
            )
            if not is_index:
                continue

            section = getattr(page, "_section", None)
            if not section:
                continue

            section_pages = getattr(section, "pages", [])
            for child in section_pages:
                if child != page and child in analysis_pages_set:
                    self.incoming_refs[child] += 0.5
                    self.outgoing_refs[page].add(child)
                    self.link_types[(page, child)] = LinkType.TOPICAL

        logger.debug(
            "knowledge_graph_section_hierarchy_complete",
            topical_links=sum(1 for lt in self.link_types.values() if lt == LinkType.TOPICAL),
        )

    def _analyze_navigation_links(self) -> None:
        """
        Analyze next/prev sequential relationships.

        Pages in a section often have prev/next relationships representing
        a reading order or logical sequence (e.g., tutorial steps, changelogs).

        Weight: 0.25 (pure navigation, lowest editorial intent)
        """
        analysis_pages = self.get_analysis_pages()
        analysis_pages_set = set(analysis_pages)

        for page in analysis_pages:
            next_page = getattr(page, "next_in_section", None)
            if next_page and next_page in analysis_pages_set:
                self.incoming_refs[next_page] += 0.25
                self.outgoing_refs[page].add(next_page)
                self.link_types[(page, next_page)] = LinkType.SEQUENTIAL

            prev_page = getattr(page, "prev_in_section", None)
            if prev_page and prev_page in analysis_pages_set:
                self.incoming_refs[prev_page] += 0.25
                self.outgoing_refs[page].add(prev_page)
                self.link_types[(page, prev_page)] = LinkType.SEQUENTIAL

        logger.debug(
            "knowledge_graph_navigation_links_complete",
            sequential_links=sum(1 for lt in self.link_types.values() if lt == LinkType.SEQUENTIAL),
        )

    def _build_link_metrics(self) -> None:
        """
        Build detailed link metrics for each page.

        Aggregates links by type into LinkMetrics objects for
        weighted connectivity scoring.
        """
        analysis_pages = self.get_analysis_pages()

        for page in analysis_pages:
            metrics = LinkMetrics()

            for (_source, target), link_type in self.link_types.items():
                if target == page:
                    if link_type == LinkType.EXPLICIT:
                        metrics.explicit += 1
                    elif link_type == LinkType.MENU:
                        metrics.menu += 1
                    elif link_type == LinkType.TAXONOMY:
                        metrics.taxonomy += 1
                    elif link_type == LinkType.RELATED:
                        metrics.related += 1
                    elif link_type == LinkType.TOPICAL:
                        metrics.topical += 1
                    elif link_type == LinkType.SEQUENTIAL:
                        metrics.sequential += 1

            # Fallback: count untracked incoming refs as explicit
            total_tracked = metrics.total_links()
            total_incoming = int(self.incoming_refs[page])
            untracked = max(0, total_incoming - total_tracked)
            metrics.explicit += untracked

            self.link_metrics[page] = metrics

        logger.debug(
            "knowledge_graph_link_metrics_built",
            pages_with_metrics=len(self.link_metrics),
        )
