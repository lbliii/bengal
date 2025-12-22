"""
Result dataclasses for graph analysis operations.

Provides typed result containers that replace complex tuple return values
with named fields for better type safety, readability, and IDE support.

All dataclasses support backward compatibility via __iter__() methods
for tuple unpacking, allowing existing code to continue working.

Classes:
    PageLayers: Partitioned pages by connectivity for streaming builds.

Example:
    >>> from bengal.analysis import KnowledgeGraph
    >>> graph = KnowledgeGraph(site)
    >>> graph.build()
    >>> layers = graph.get_layers()
    >>> # Named attribute access (preferred)
    >>> print(f"Hubs: {len(layers.hubs)}, Leaves: {len(layers.leaves)}")
    >>> # Tuple unpacking (backward compatible)
    >>> hubs, mid_tier, leaves = layers
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page


@dataclass
class PageLayers:
    """
    Page layers partitioned by connectivity for streaming builds.

    Pages are partitioned into three layers based on their connectivity
    scores to enable hub-first streaming builds:

    - Hubs: High connectivity pages (top 10%) - process first, keep in memory
    - Mid-tier: Medium connectivity pages (next 30%) - batch processing
    - Leaves: Low connectivity pages (remaining 60%) - stream and release

    Attributes:
        hubs: High connectivity pages (top 10% by connectivity score)
        mid_tier: Medium connectivity pages (next 30%)
        leaves: Low connectivity pages (remaining 60%)
    """

    hubs: list[Page]
    mid_tier: list[Page]
    leaves: list[Page]

    def __iter__(self):
        """Allow tuple unpacking for backward compatibility."""
        yield self.hubs
        yield self.mid_tier
        yield self.leaves
