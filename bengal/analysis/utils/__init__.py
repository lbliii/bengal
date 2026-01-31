"""
Shared utilities for Bengal analysis package.

This module provides common utilities used across analysis subpackages
to reduce code duplication and ensure consistent behavior.

Modules:
    pages: Page filtering utilities (get_content_pages)
    validation: Graph state validation (@require_built decorator)
    traversal: Graph traversal algorithms (BFS utilities)
    indexing: Inverted index builders for efficient lookups
    scoring: Score sorting and ranking utilities

Example:
    >>> from bengal.analysis.utils import get_content_pages, require_built
    >>> pages = get_content_pages(graph)
    >>> # Or use the decorator
    >>> @require_built
    ... def my_analysis_method(self): ...

"""

from bengal.analysis.utils.constants import DEFAULT_HUB_THRESHOLD, DEFAULT_LEAF_THRESHOLD
from bengal.analysis.utils.indexing import build_inverted_index
from bengal.analysis.utils.pages import get_content_pages
from bengal.analysis.utils.scoring import top_n_by_score
from bengal.analysis.utils.traversal import bfs_distances, bfs_path
from bengal.analysis.utils.validation import require_built

__all__ = [
    "DEFAULT_HUB_THRESHOLD",
    "DEFAULT_LEAF_THRESHOLD",
    "bfs_distances",
    "bfs_path",
    "build_inverted_index",
    "get_content_pages",
    "require_built",
    "top_n_by_score",
]
