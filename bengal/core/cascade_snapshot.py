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
- Supports eager merge via apply_to_page() for duality elimination

Eager Cascade Merge:
    After building the snapshot, cascade values are merged into each page's
    metadata via apply_to_page(). This eliminates the duality between
    page.metadata.get("type") and page.type - they now return the same value.

Usage:
    # At build start
    snapshot = CascadeSnapshot.build(content_dir, sections)
    site._cascade_snapshot = snapshot

    # Apply cascade values to pages (eager merge)
    for page in pages:
        snapshot.apply_to_page(page, content_dir)

    # After eager merge, both access patterns return the same value
    assert page.metadata.get("type") == page.type

Benefits:
- No timing issues (snapshot built before pages processed)
- Lock-free parallel rendering (frozen data structure)
- Clean incremental builds (atomic snapshot swap)
- Single source of truth (metadata.get() == property access)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from bengal.utils.paths.normalize import to_posix

if TYPE_CHECKING:
    from collections.abc import Mapping

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

    @staticmethod
    def _normalize_path_static(section_path: str, content_dir: str | None) -> str:
        """
        Normalize section path to content-relative format for lookup.

        This is a static method so it can be used by both build() and resolve().

        Handles the path representation inconsistency between:
        - Section.path: Absolute Path (e.g., /Users/foo/site/content/docs)
        - PageCore.section: Absolute path string
        - CascadeSnapshot._data keys: Content-relative strings (e.g., "docs")

        Args:
            section_path: Section path in any format (absolute or relative)
            content_dir: Content directory for computing relative paths

        Returns:
            Content-relative path string suitable for _data lookup
        """
        if not section_path or section_path in ("", "."):
            return ""

        # Normalize path separators for cross-platform consistency
        normalized = to_posix(section_path)

        # If already relative (no leading /), use as-is
        if not normalized.startswith("/"):
            return normalized

        # Try to make absolute path relative to content_dir
        if content_dir:
            try:
                content_dir_path = Path(content_dir)
                section_path_obj = Path(section_path)
                rel = section_path_obj.relative_to(content_dir_path)
                result = to_posix(rel)
                # Normalize "." to empty string
                return "" if result == "." else result
            except ValueError:
                # Path not relative to content_dir, try other approaches
                pass

        # Fallback: strip common content directory patterns
        # This handles test scenarios where paths don't match the site structure
        for prefix in ("/content/", "content/"):
            if normalized.endswith(prefix.rstrip("/")):
                return ""
            idx = normalized.find(prefix)
            if idx != -1:
                return normalized[idx + len(prefix) :]

        # Last resort: return as-is (will likely miss, but won't crash)
        return normalized

    def _normalize_section_path(self, section_path: str) -> str:
        """
        Normalize section path to content-relative format for lookup.

        Delegates to static method with instance's content_dir.
        """
        return self._normalize_path_static(section_path, self._content_dir)

    def get_cascade_for_section(self, section_path: str) -> Mapping[str, Any]:
        """
        Get the cascade dict defined by a specific section.

        This returns only the cascade values explicitly defined in that
        section's _index.md, not inherited values from parent sections.

        Returns an immutable view (MappingProxyType) to preserve thread-safety
        guarantees - callers cannot mutate the internal snapshot data.

        Args:
            section_path: Path to section (absolute or relative, e.g., "docs/guide")

        Returns:
            Immutable view of cascade dict for that section, or empty dict if none.
        """
        normalized = self._normalize_section_path(section_path)
        data = self._data.get(normalized, {})
        # Return immutable view to prevent callers from corrupting snapshot
        return MappingProxyType(data) if data else {}

    def resolve(self, section_path: str, key: str) -> Any:
        """
        Resolve a cascade value by walking up the section hierarchy.

        This implements the cascade inheritance: a page in "docs/guide/advanced"
        will inherit cascade values from "docs/guide", then "docs", then root.
        The first section that defines the key wins (nearest ancestor).

        Args:
            section_path: Path to the page's section (absolute or relative).
                Absolute paths are normalized to content-relative format.
            key: Cascade key to look up (e.g., "type", "layout", "variant")

        Returns:
            The cascade value from the nearest ancestor section, or None.

        Complexity:
            O(depth) where depth is the section nesting level (typically 2-4)
        """
        # Normalize path to content-relative format for consistent lookup
        path = self._normalize_section_path(section_path)

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
            section_path: Path to the page's section (absolute or relative).
                Absolute paths are normalized to content-relative format.

        Returns:
            Merged cascade dict with all inherited and local values.
            Returns a new dict (safe to modify without affecting snapshot).
        """
        result: dict[str, Any] = {}

        # Normalize path to content-relative format for consistent lookup
        normalized_path = self._normalize_section_path(section_path)

        # Build path components from root to target
        if not normalized_path or normalized_path == ".":
            components: list[str] = []
        else:
            parts = normalized_path.split("/")
            components = ["/".join(parts[: i + 1]) for i in range(len(parts))]

        # Check root first
        root_cascade = self._data.get("", {}) or self._data.get(".", {})
        result.update(root_cascade)

        # Walk from root to target, child overrides parent
        for path in components:
            cascade = self._data.get(path, {})
            result.update(cascade)

        return result

    def get_cascade_keys(self, section_path: str) -> set[str]:
        """
        Get all keys that could be cascaded to a section path.

        Walks up the section hierarchy collecting all cascade keys from
        each ancestor section. This is useful for determining which keys
        need to be applied to a page.

        Args:
            section_path: Path to the page's section (absolute or relative).
                Absolute paths are normalized to content-relative format.

        Returns:
            Set of all cascade keys that could apply to this section.

        Complexity:
            O(depth * keys) where depth is the section nesting level
        """
        keys: set[str] = set()
        path = self._normalize_section_path(section_path)

        while path:
            if path in self._data:
                keys.update(self._data[path].keys())
            if "/" in path:
                path = path.rsplit("/", 1)[0]
            else:
                break

        # Check root cascade
        root = self._data.get("", {}) or self._data.get(".", {})
        keys.update(root.keys())
        return keys

    def _get_section_path_from_page(self, page: Any, content_dir: Path) -> str:
        """
        Extract and normalize section path from a page object.

        Handles different page types (Page, PageProxy) and their various
        ways of storing section information.

        Args:
            page: Page or PageProxy object
            content_dir: Content directory for relative path computation

        Returns:
            Normalized section path string for cascade lookup
        """
        # Try to get section path from various sources
        section_path = ""

        # PageProxy stores section in core.section
        if (
            hasattr(page, "core")
            and page.core is not None
            and hasattr(page.core, "section")
            and page.core.section
        ):
            section_path = page.core.section

        # Page has _section attribute
        if (
            not section_path
            and hasattr(page, "_section")
            and page._section is not None
            and hasattr(page._section, "path")
            and page._section.path is not None
        ):
            try:
                section_path = str(page._section.path.relative_to(content_dir))
            except ValueError:
                # Use normalization that handles /content/ patterns
                section_path = str(page._section.path)

        # Fallback: derive from source_path
        if not section_path and hasattr(page, "source_path"):
            try:
                rel_path = page.source_path.relative_to(content_dir)
                # Section is the parent directory
                if rel_path.parent != Path("."):
                    section_path = str(rel_path.parent)
            except (ValueError, AttributeError):
                # source_path not relative to content_dir - use path normalization
                # This handles test scenarios with mismatched paths
                parent = page.source_path.parent
                section_path = str(parent)

        return self._normalize_section_path(section_path)

    def apply_to_page(self, page: Any, content_dir: Path) -> set[str]:
        """
        Merge resolved cascade values into page's metadata.

        This implements eager cascade merge: after calling this method,
        `page.metadata.get("key")` and `page.key` will return the same value
        for cascadable keys, eliminating the duality between the two access
        patterns.

        Args:
            page: Page or PageProxy object with a mutable `metadata` dict
            content_dir: Content directory root for section path calculation

        Returns:
            Set of keys that were added from cascade (not overwritten).

        Behavior:
            - Frontmatter values take precedence over cascade
            - Only keys defined in ancestor cascade blocks are considered
            - Tracks which keys came from cascade via `_cascade_keys` metadata
        """
        section_path = self._get_section_path_from_page(page, content_dir)
        applied_keys: set[str] = set()

        # Get all keys that could be cascaded to this section
        for key in self.get_cascade_keys(section_path):
            if key not in page.metadata:  # Frontmatter wins
                value = self.resolve(section_path, key)
                if value is not None:
                    page.metadata[key] = value
                    applied_keys.add(key)

        # Track origin for debugging and provenance
        existing_cascade_keys = page.metadata.get("_cascade_keys", [])
        if applied_keys:
            page.metadata["_cascade_keys"] = list(set(existing_cascade_keys) | applied_keys)

        return applied_keys

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

            # Compute and normalize section path for consistent lookups
            if section.path is None:
                # Virtual section or root
                section_path = ""
            else:
                # Use the shared normalization logic for consistent key format
                section_path = cls._normalize_path_static(
                    str(section.path), str(content_dir)
                )

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
        normalized = self._normalize_section_path(section_path)
        return normalized in self._data
