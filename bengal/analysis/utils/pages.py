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

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from bengal.protocols import PageLike


class _GraphLike(Protocol):
    """Protocol for graph-like objects with get_analysis_pages (breaks kg->pages cycle)."""

    def get_analysis_pages(self) -> list[PageLike]: ...


def stable_page_id(site: Any, page: Any) -> str:
    """
    Return a stable, build-reproducible id for a page.

    Hashes the *site-relative* source path with a fixed algorithm. Python's
    built-in ``hash()`` is per-process randomized (PYTHONHASHSEED) and an
    absolute path varies by checkout location — both make derived data
    (``graph.json`` node ids, analysis ordering) differ between otherwise
    identical builds, which breaks byte-reproducible output and the warm==cold
    parity contract. A deterministic hash of the site-relative path is stable
    across builds and machines while staying unique per page.

    This is the single source of truth for the graph node id (consumed by
    :meth:`GraphVisualizer._get_page_id`) and the canonical page-ordering key
    (consumed by ``GraphBuilder.get_analysis_pages``), so that nodes are emitted
    in id order and every analysis iterates a build-stable order.

    Args:
        site: Site instance (used for ``root_path`` to relativize source paths).
        page: Page object.

    Returns:
        Stable string id for the page.
    """
    from bengal.utils.primitives.hashing import hash_str

    source_path = getattr(page, "source_path", None)
    if source_path is not None:
        try:
            rel: Any = source_path
            root = getattr(site, "root_path", None)
            if root is not None:
                # Canonicalize both sides before taking the relative path: the
                # page source and the site root can carry different symlink forms
                # (e.g. macOS ``/var`` vs ``/private/var``), which would make a
                # naive ``relative_to`` fall back to the absolute
                # (location-dependent) path and reintroduce nondeterminism across
                # build locations.
                try:
                    rel = Path(source_path).resolve().relative_to(Path(root).resolve())
                except ValueError, OSError, TypeError:
                    # TypeError: root is not path-like. Fall back to a plain
                    # relative_to, then to the source path itself.
                    try:
                        rel = Path(source_path).relative_to(root)
                    except ValueError, TypeError:
                        rel = source_path
            return hash_str(Path(rel).as_posix(), truncate=16)
        except TypeError:
            # source_path is not path-like (e.g. a test Mock). Fall through to the
            # location-independent seed below rather than crashing.
            pass

    # Generated/virtual pages without a usable source file: derive a stable id
    # from a location-independent identifier.
    try:
        seed = str(page.href)
    except Exception:
        seed = str(getattr(page, "title", "") or id(page))
    return hash_str(seed, truncate=16)


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
