"""
Navigation tree node model.

Single node in a hierarchical navigation tree with O(1) lookups.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.protocols import SectionLike


@dataclass(slots=True)
class NavNode:
    """
    Hierarchical navigation node for pre-computed trees.

    Designed for memory efficiency and Jinja2 compatibility.

    IMPORTANT: The `_path` field stores site_path (WITHOUT baseurl) for cache
    efficiency and internal lookups. Templates should use NavNodeProxy.href
    which applies baseurl automatically.

    """

    id: str
    title: str
    _path: str  # NOTE: This is site_path (without baseurl). See NavNodeProxy.href for public URL.
    icon: str | None = None
    weight: int = 0
    children: list[NavNode] = field(default_factory=list)
    page: Page | None = None
    section: SectionLike | None = None

    # State flags (populated by NavTreeContext)
    is_index: bool = False
    is_current: bool = False
    is_in_trail: bool = False
    is_expanded: bool = False

    _depth: int = 0

    @property
    def has_children(self) -> bool:
        """True if this node has child nodes.

        Cost: O(1) — len() on list.
        """
        return len(self.children) > 0

    @property
    def depth(self) -> int:
        """Nesting level (0 = top level).

        Cost: O(1) — direct attribute read.
        """
        return self._depth

    def walk(self) -> Iterator[NavNode]:
        """Iterate over this node and all descendants."""
        yield self
        for child in self.children:
            yield from child.walk()

    # --- Jinja2 Compatibility (Dict-like access) ---

    def __getitem__(self, key: str) -> Any:
        """Allow node['attr'] in templates."""
        try:
            return getattr(self, key)
        except AttributeError as e:
            raise KeyError(key) from e

    def get(self, key: str, default: Any = None) -> Any:
        """Allow node.get('attr', default) in templates."""
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        """Allow iteration over keys in templates."""
        return [
            "id",
            "title",
            "_path",
            "href",  # For templates (via NavNodeProxy)
            "icon",
            "weight",
            "children",
            "is_index",
            "is_current",
            "is_in_trail",
            "is_expanded",
            "has_children",
            "depth",
        ]
