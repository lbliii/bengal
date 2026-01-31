"""
Immutable cascade snapshot for thread-safe cascade resolution.

This module provides a frozen data structure that captures all cascade metadata
from _index.md files at build time. The snapshot is computed once and shared
across all render threads without locks.

Architecture:
- CascadeSnapshot is created at the start of content discovery
- Contains a mapping of section_path -> cascade dict
- Provides O(depth) resolve() for cascade key lookup
- Immutable (frozen dataclass) for thread-safety in free-threading builds

Usage:
    # At build start
    snapshot = CascadeSnapshot.build(content_dir, sections)
    site._cascade_snapshot = snapshot

    # At render time (any thread)
    page_type = site.cascade.resolve(section_path, "type")

Benefits over CascadeEngine:
- No timing issues (snapshot built before pages processed)
- Lock-free parallel rendering (frozen data structure)
- Clean incremental builds (atomic snapshot swap)
- No special-casing for _index.md caching
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.section import Section


@dataclass(frozen=True, slots=True)
class CascadeSnapshot:
    """
    Immutable cascade data computed once per build.

    This frozen dataclass captures cascade metadata from all _index.md files
    and provides thread-safe resolution without locks. The snapshot is
    inherently safe for concurrent access in free-threaded Python because
    it cannot be mutated after creation.

    Attributes:
        _data: Mapping of section_path (str) to cascade dict.
               e.g., {"docs": {"type": "doc", "layout": "docs-layout"}}
        _content_dir: Content directory path for relative path computation.

    Example:
        >>> snapshot = CascadeSnapshot.build(content_dir, sections)
        >>> snapshot.resolve("docs/guide", "type")
        "doc"  # Inherited from "docs" section
    """

    _data: dict[str, dict[str, Any]] = field(default_factory=dict)
    _content_dir: str = ""

    def get_cascade_for_section(self, section_path: str) -> dict[str, Any]:
        """
        Get the cascade dict defined by a specific section.

        This returns only the cascade values explicitly defined in that
        section's _index.md, not inherited values from parent sections.

        Args:
            section_path: Relative path to section (e.g., "docs/guide")

        Returns:
            Cascade dict for that section, or empty dict if none defined.
        """
        return self._data.get(section_path, {})

    def resolve(self, section_path: str, key: str) -> Any:
        """
        Resolve a cascade value by walking up the section hierarchy.

        This implements the cascade inheritance: a page in "docs/guide/advanced"
        will inherit cascade values from "docs/guide", then "docs", then root.
        The first section that defines the key wins (nearest ancestor).

        Args:
            section_path: Relative path to the page's section (e.g., "docs/guide")
            key: Cascade key to look up (e.g., "type", "layout", "variant")

        Returns:
            The cascade value from the nearest ancestor section, or None.

        Complexity:
            O(depth) where depth is the section nesting level (typically 2-4)
        """
        path = section_path
        while path:
            cascade = self._data.get(path, {})
            if key in cascade:
                return cascade[key]
            # Move up: "docs/guide/advanced" -> "docs/guide" -> "docs" -> ""
            if "/" in path:
                path = "/".join(path.split("/")[:-1])
            else:
                # Check root level cascade (path == "." or section name without /)
                break

        # Check root cascade (empty string or ".")
        root_cascade = self._data.get("", {}) or self._data.get(".", {})
        return root_cascade.get(key)

    def resolve_all(self, section_path: str) -> dict[str, Any]:
        """
        Resolve all cascade values for a section path.

        This computes the merged cascade by walking from root to the target
        section, with child sections overriding parent values.

        Args:
            section_path: Relative path to the page's section

        Returns:
            Merged cascade dict with all inherited and local values.
        """
        result: dict[str, Any] = {}

        # Build path components from root to target
        if not section_path or section_path == ".":
            components: list[str] = []
        else:
            parts = section_path.split("/")
            components = ["/".join(parts[: i + 1]) for i in range(len(parts))]

        # Check root first
        root_cascade = self._data.get("", {}) or self._data.get(".", {})
        result.update(root_cascade)

        # Walk from root to target, child overrides parent
        for path in components:
            cascade = self._data.get(path, {})
            result.update(cascade)

        return result

    @classmethod
    def build(
        cls,
        content_dir: Path,
        sections: list[Section],
        root_cascade: dict[str, Any] | None = None,
    ) -> CascadeSnapshot:
        """
        Build a cascade snapshot from all sections.

        This scans all sections and extracts cascade metadata from their
        index pages (_index.md). The resulting snapshot is immutable and
        can be safely shared across threads.

        Args:
            content_dir: Root content directory for computing relative paths.
            sections: List of all sections in the site.
            root_cascade: Optional cascade from root-level pages (e.g., content/index.md)
                         that applies site-wide.

        Returns:
            Frozen CascadeSnapshot with all cascade data.

        Note:
            Sections without index pages or without cascade metadata are
            skipped. This is normal for leaf sections that inherit cascade.
        """
        data: dict[str, dict[str, Any]] = {}

        # Add root cascade if provided (from pages not in any section)
        if root_cascade:
            data[""] = dict(root_cascade)

        for section in sections:
            # Get cascade from index page metadata first (preferred)
            # Fall back to section.metadata["cascade"] for backward compatibility
            # with tests and programmatically-created sections
            cascade = {}
            if section.index_page:
                cascade = section.index_page.metadata.get("cascade", {})
            if not cascade:
                cascade = section.metadata.get("cascade", {})
            if not cascade:
                continue

            # Compute relative section path
            if section.path is None:
                # Virtual section or root
                section_path = ""
            else:
                try:
                    section_path = str(section.path.relative_to(content_dir))
                except ValueError:
                    # Path not relative to content_dir, use as-is
                    section_path = str(section.path)

            # Normalize path (handle "." for root)
            if section_path == ".":
                section_path = ""

            data[section_path] = dict(cascade)  # Copy to ensure immutability

        return cls(_data=data, _content_dir=str(content_dir))

    @classmethod
    def empty(cls) -> CascadeSnapshot:
        """
        Create an empty cascade snapshot.

        Useful for tests or sites without any cascade metadata.

        Returns:
            Empty frozen CascadeSnapshot.
        """
        return cls(_data={}, _content_dir="")

    def __len__(self) -> int:
        """Return number of sections with cascade data."""
        return len(self._data)

    def __contains__(self, section_path: str) -> bool:
        """Check if a section has cascade data defined."""
        return section_path in self._data
