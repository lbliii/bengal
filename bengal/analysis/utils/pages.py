"""
Page filtering utilities for analysis modules.

Provides consistent page filtering across all analysis components,
ensuring autodoc pages and generated pages are excluded uniformly.

This centralizes the filtering logic that was previously duplicated in:
- page_rank.py
- community_detection.py
- path_analysis.py
- suggestions.py
- visualizer.py
- builder.py

Example:
    >>> from bengal.analysis.utils import get_content_pages
    >>> pages = get_content_pages(graph)
    >>> # Now use pages for analysis...

"""

from typing import Protocol

from bengal.protocols import PageLike


class _GraphLike(Protocol):
    """Protocol for graph-like objects with get_analysis_pages (breaks kg->pages cycle)."""

    def get_analysis_pages(self) -> list[PageLike]: ...


def get_content_pages(
    graph: _GraphLike,
    *,
    exclude_generated: bool = True,
) -> list[PageLike]:
    """
    Get pages suitable for content analysis.

    Retrieves analysis pages from the graph (which already excludes autodoc
    pages if configured) and optionally filters out generated pages like
    taxonomy index pages.

    Args:
        graph: Graph-like instance with get_analysis_pages() (e.g. KnowledgeGraph)
        exclude_generated: If True, exclude pages with _generated metadata.
                          Default True. Generated pages include taxonomy
                          pages (tag pages, category pages) that are
                          system-created rather than author-written.

    Returns:
        List of pages suitable for content analysis.

    Example:
        >>> pages = get_content_pages(graph)
        >>> # Returns only author-written content pages

        >>> pages = get_content_pages(graph, exclude_generated=False)
        >>> # Includes generated taxonomy pages

    """
    # Get analysis pages (already excludes autodoc if configured)
    pages = graph.get_analysis_pages()

    if exclude_generated:
        pages = [p for p in pages if not p.metadata.get("_generated")]

    return pages
