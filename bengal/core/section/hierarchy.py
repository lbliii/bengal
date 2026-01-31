"""
Section Hierarchy Mixin - Tree traversal and identity.

Provides tree structure traversal and parent-child relationship methods
for sections. Handles depth calculation, root finding, subsection sorting,
and identity operations (hash/equality).

Required Host Attributes:
- name: str
- path: Path | None
- parent: Section | None
- subsections: list[Section]
- metadata: dict[str, Any]
- index_page: Page | None
- _virtual: bool
- _relative_url_override: str | None

Related Modules:
bengal.core.section: Section dataclass using this mixin
bengal.core.section.navigation: URL generation for sections

Example:
    >>> section = site.get_section("blog/2024")
    >>> section.depth
2
    >>> section.root.name
    'content'

"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.page import Page
    from bengal.core.section import Section


class SectionHierarchyMixin:
    """
    Tree structure traversal and relationships.

    This mixin handles:
    - Parent/child navigation (parent, root, subsections)
    - Depth and hierarchy calculation
    - Subsection sorting by weight
    - Tree walking (walk)
    - Identity operations (__hash__, __eq__)
    - Icon property from index page metadata

    """

    # =========================================================================
    # HOST CLASS ATTRIBUTES
    # =========================================================================
    # Type hints for attributes provided by the host dataclass.
    # These are NOT defined here - they're declared for type checking only.

    name: str
    path: Path | None
    parent: Section | None
    subsections: list[Section]
    metadata: dict[str, Any]
    index_page: Page | None
    _virtual: bool
    _relative_url_override: str | None

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def hierarchy(self) -> list[str]:
        """
        Get the full hierarchy path of this section.

        Returns:
            List of section names from root to this section

        Example:
            >>> section = site.get_section("docs/api/core")
            >>> section.hierarchy
            ['docs', 'api', 'core']
        """
        if self.parent:
            return [*self.parent.hierarchy, self.name]
        return [self.name]

    @property
    def depth(self) -> int:
        """
        Get the depth of this section in the hierarchy.

        Returns:
            Nesting depth (1 for root, 2 for first-level sections, etc.)

        Example:
            >>> site.root_section.depth
            1
            >>> site.get_section("blog/2024").depth
            3
        """
        return len(self.hierarchy)

    @property
    def root(self) -> Section:
        """
        Get the root section of this section's hierarchy.

        Traverses up the parent chain until reaching either:
        - A section with no parent (topmost ancestor)
        - A section with nav_root: true metadata (navigation boundary)
        - The top-level section inside a version folder (for versioned content)

        The nav_root metadata allows sections to act as their own navigation
        root, useful for autodoc collections (e.g., /api/python/) that should
        not show their parent aggregator (/api/) in the sidebar.

        For versioned content in _versions/<id>/docs/, the root is docs/
        (the top-level content section within that version), not the version
        folder or _versions/ itself.

        Returns:
            The navigation root section

        Example:
            {% set root_section = page._section.root %}
        """
        current: Section = self  # type: ignore[assignment]
        while current.parent:
            # Stop if current section declares itself as a nav root
            if current.metadata.get("nav_root"):
                return current
            # Stop at top-level section inside a version folder
            # Hierarchy is: _versions/<version_id>/<section>/...
            # We want <section> as root, not <version_id> or _versions
            parent = current.parent
            if parent.parent and parent.parent.name == "_versions":
                # current.parent is the version folder (e.g., v1)
                # current is the top-level section (e.g., docs)
                return current
            current = parent
        return current

    @cached_property
    def icon(self) -> str | None:
        """
        Get section icon from index page metadata (cached).

        Icons can be specified in a section's _index.md frontmatter:

            ---
            title: API Reference
            icon: book
            ---

        The icon name should match a Phosphor icon in the icon library
        (e.g., 'book', 'folder', 'terminal', 'code').

        Returns:
            Icon name string, or None if no icon is specified

        Example:
            {% if section.icon %}
              {{ icon(section.icon, size=16) }}
            {% endif %}

        Performance:
            Uses @cached_property to avoid repeated dict lookups on each access.
        """
        # First check index page metadata (preferred source)
        if (
            self.index_page
            and hasattr(self.index_page, "metadata")
            and (icon_value := self.index_page.metadata.get("icon"))
        ):
            return str(icon_value) if icon_value else None
        # Fall back to section metadata (in case copied during add_page)
        result = self.metadata.get("icon")
        return str(result) if result else None

    @cached_property
    def sorted_subsections(self) -> list[Section]:
        """
        Get subsections sorted by weight (ascending), then by title (CACHED).

        This property is cached after first access for O(1) subsequent lookups.
        The sort is computed once and reused across all template renders.

        Subsections without a weight field in their index page metadata
        are treated as having weight=infinity (appear at end). Lower weights appear first.

        Performance:
            - First access: O(m log m) where m = number of subsections
            - Subsequent accesses: O(1) cached lookup
            - Memory cost: O(m) to store sorted list

        Returns:
            List of subsections sorted by weight, then title

        Example:
            {% for subsection in section.sorted_subsections %}
              <h3>{{ subsection.title }}</h3>
            {% endfor %}
        """
        from bengal.core.utils.sorting import DEFAULT_WEIGHT

        return sorted(
            self.subsections, key=lambda s: (s.metadata.get("weight", DEFAULT_WEIGHT), s.title.lower())
        )

    # =========================================================================
    # METHODS
    # =========================================================================

    def add_subsection(self, section: Section) -> None:
        """
        Add a subsection to this section.

        Sets the parent reference on the child section.

        Args:
            section: Child section to add
        """
        section.parent = self  # type: ignore[assignment]
        self.subsections.append(section)

    def walk(self) -> list[Section]:
        """
        Iteratively walk through all sections in the hierarchy.

        Returns:
            List of all sections (self and descendants)

        Example:
            >>> for section in root.walk():
            ...     print(section.name)
        """
        sections: list[Section] = [self]  # type: ignore[assignment]
        stack = list(self.subsections)

        while stack:
            section = stack.pop()
            sections.append(section)
            stack.extend(section.subsections)

        return sections

    # =========================================================================
    # IDENTITY
    # =========================================================================

    def __hash__(self) -> int:
        """
        Hash based on section path (or name for virtual sections) for stable identity.

        The hash is computed from the section's path, which is immutable
        throughout the section lifecycle. This allows sections to be stored
        in sets and used as dictionary keys.

        For virtual sections (path=None), uses the name and _relative_url_override
        for hashing to ensure stable identity.

        Returns:
            Integer hash of the section path or name
        """
        if self.path is None:
            # Virtual sections: hash by name and URL
            return hash((self.name, self._relative_url_override))
        return hash(self.path)

    def __eq__(self, other: Any) -> bool:
        """
        Sections are equal if they have the same path (or name+URL for virtual).

        Equality is based on path only, not on pages or other mutable fields.
        This means two Section objects representing the same directory are
        considered equal, even if their contents differ.

        For virtual sections (path=None), equality is based on name and URL.

        Args:
            other: Object to compare with

        Returns:
            True if other is a Section with the same path
        """
        if not isinstance(other, SectionHierarchyMixin):
            return NotImplemented
        if self.path is None and other.path is None:
            # Both virtual: compare by name and URL
            return (self.name, self._relative_url_override) == (
                other.name,
                other._relative_url_override,
            )
        return self.path == other.path
