"""
Immutable cascade snapshot for thread-safe cascade resolution.

This module provides a frozen data structure that captures all cascade metadata
from _index.md files at build time. The snapshot is computed once and shared
across all render threads without locks.

Architecture:
- CascadeSnapshot is created at the start of content discovery
- Contains raw cascade blocks per section (_data) and pre-merged cascade (_merged)
- Pre-merged cascade enables O(1) resolution (no tree walking needed)
- Cascade inheritance: child sections inherit from parents, local values override
- Immutable (frozen dataclass) for thread-safety in free-threading builds

Pre-Merged Cascade:
    The _merged field stores fully resolved cascade for each section path.
    This includes inherited values from all parent sections, with child
    values overriding parent values. Resolution becomes O(1) instead of O(depth).

    Example:
        _data (raw blocks):
            "docs": {"type": "doc"}
            "docs/guide": {"layout": "sidebar"}

        _merged (pre-computed):
            "docs": {"type": "doc"}
            "docs/guide": {"type": "doc", "layout": "sidebar"}  # inherits type!

Cascade Block Merging:
    Unlike the previous design where child sections had to repeat parent
    cascade values, the pre-merged approach automatically inherits:

        # docs/_index.md
        cascade:
          type: doc

        # docs/guide/_index.md (only needs to add new values)
        cascade:
          layout: sidebar

        # Pages in docs/guide/ automatically get both type AND layout!

Usage:
    # At build start
    snapshot = CascadeSnapshot.build(content_dir, sections)
    site._cascade_snapshot = snapshot

    # Resolution is O(1) via pre-merged data
    snapshot.resolve("docs/guide", "type")  # Returns "doc" (inherited)

    # Or use with CascadeView for dict-like access
    from bengal.core.cascade import CascadeView
    view = CascadeView.for_page(frontmatter, "docs/guide", snapshot)

Benefits:
- O(1) resolution (pre-merged, no tree walking)
- Cascade inheritance (child inherits parent automatically)
- Lock-free parallel rendering (frozen data structure)
- Clean incremental builds (atomic snapshot swap)
- Single source of truth for cascade values
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
        _data: Mapping of section_path (str) to RAW cascade dict (only local values).
               e.g., {"docs": {"type": "doc"}, "docs/guide": {"layout": "sidebar"}}
               Used for get_cascade_for_section() and backward compatibility.

        _merged: Mapping of section_path (str) to MERGED cascade dict (inherited + local).
                 e.g., {"docs": {"type": "doc"}, "docs/guide": {"type": "doc", "layout": "sidebar"}}
                 Used for O(1) resolution via resolve() and get_cascade_keys().

        _content_dir: Content directory path for relative path computation.

    Example:
        >>> snapshot = CascadeSnapshot.build(content_dir, sections)
        >>> snapshot.resolve("docs/guide", "type")
        "doc"  # Inherited from "docs" section (O(1) lookup in _merged)
    """

    _data: dict[str, dict[str, Any]] = field(default_factory=dict)
    _merged: dict[str, dict[str, Any]] = field(default_factory=dict)
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
        Resolve a cascade value using pre-merged cascade data.

        With pre-merged cascade, resolution is O(1): we look up the section's
        merged cascade dict directly. The merged dict already contains all
        inherited values from parent sections.

        For section paths not explicitly in _merged (e.g., deeply nested paths
        without their own cascade), we fall back to walking up to find the
        nearest ancestor with merged data.

        Args:
            section_path: Path to the page's section (absolute or relative).
                Absolute paths are normalized to content-relative format.
            key: Cascade key to look up (e.g., "type", "layout", "variant")

        Returns:
            The cascade value, or None if not found.

        Complexity:
            O(1) for paths in _merged, O(depth) fallback for unknown paths.
        """
        # Normalize path to content-relative format for consistent lookup
        path = self._normalize_section_path(section_path)

        # Use pre-merged data if available, otherwise fall back to _data tree walking
        # (backward compatibility for direct construction without from_data() or build())
        use_merged = bool(self._merged)
        data_source = self._merged if use_merged else self._data

        # Fast path: direct lookup in data source
        if path in data_source:
            value = data_source[path].get(key)
            if value is not None or (use_merged and key in data_source[path]):
                return value
            # If using _data (not merged), continue to walk up for inheritance
            if use_merged:
                return None  # _merged already has inherited values

        # Walk up to find nearest ancestor with data
        # For _merged: handles unregistered deep paths
        # For _data: implements cascade inheritance
        while path:
            if path in data_source:
                value = data_source[path].get(key)
                if value is not None:
                    return value
            if "/" in path:
                path = path.rsplit("/", 1)[0]
            else:
                break

        # Check root cascade
        root_data = data_source.get("", {}) or data_source.get(".", {})
        return root_data.get(key)

    def resolve_all(self, section_path: str) -> dict[str, Any]:
        """
        Resolve all cascade values for a section path.

        With pre-merged cascade, this is O(1): we return a copy of the
        section's merged cascade dict. For paths not in _merged, we
        fall back to finding the nearest ancestor or computing the merge.

        Args:
            section_path: Path to the page's section (absolute or relative).
                Absolute paths are normalized to content-relative format.

        Returns:
            Merged cascade dict with all inherited and local values.
            Returns a new dict (safe to modify without affecting snapshot).
        """
        # Normalize path to content-relative format for consistent lookup
        normalized_path = self._normalize_section_path(section_path)

        # Use pre-merged data if available
        if self._merged:
            # Fast path: direct lookup in pre-merged data
            if normalized_path in self._merged:
                return dict(self._merged[normalized_path])

            # Fallback: walk up to find nearest ancestor with merged data
            path = normalized_path
            while path:
                if path in self._merged:
                    return dict(self._merged[path])
                if "/" in path:
                    path = path.rsplit("/", 1)[0]
                else:
                    break

            # Return root cascade
            root_merged = self._merged.get("", {}) or self._merged.get(".", {})
            return dict(root_merged)

        # Backward compatibility: compute merge from _data (tree walking)
        result: dict[str, Any] = {}

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

        With pre-merged cascade, this is O(1): we return the keys from
        the section's merged cascade dict. For paths not in _merged,
        we fall back to finding the nearest ancestor or computing keys.

        Args:
            section_path: Path to the page's section (absolute or relative).
                Absolute paths are normalized to content-relative format.

        Returns:
            Set of all cascade keys that could apply to this section.

        Complexity:
            O(1) for paths in _merged, O(depth) fallback for unknown paths.
        """
        path = self._normalize_section_path(section_path)

        # Use pre-merged data if available
        if self._merged:
            # Fast path: direct lookup in pre-merged data
            if path in self._merged:
                return set(self._merged[path].keys())

            # Fallback: walk up to find nearest ancestor with merged data
            while path:
                if path in self._merged:
                    return set(self._merged[path].keys())
                if "/" in path:
                    path = path.rsplit("/", 1)[0]
                else:
                    break

            # Return root cascade keys
            root_merged = self._merged.get("", {}) or self._merged.get(".", {})
            return set(root_merged.keys())

        # Backward compatibility: collect keys from _data (tree walking)
        keys: set[str] = set()
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

        Process:
            1. Collect raw cascade blocks from each section's _index.md
            2. Pre-compute merged cascade for each section path:
               - Start with root cascade (if any)
               - For each section path, inherit parent's merged cascade
               - Override with section's local cascade block

        Args:
            content_dir: Root content directory for computing relative paths.
            sections: List of all sections in the site.
            root_cascade: Optional cascade from root-level pages (e.g., content/index.md)
                         that applies site-wide.

        Returns:
            Frozen CascadeSnapshot with raw (_data) and merged (_merged) cascade.

        Note:
            Sections without index pages or without cascade metadata still
            get entries in _merged (inheriting from parent), but no entry
            in _data.
        """
        data: dict[str, dict[str, Any]] = {}
        all_section_paths: list[str] = []

        # Add root cascade if provided (from pages not in any section)
        if root_cascade:
            data[""] = dict(root_cascade)

        # Phase 1: Collect raw cascade blocks and all section paths
        for section in sections:
            # Compute and normalize section path for consistent lookups
            if section.path is None:
                section_path = ""
            else:
                section_path = cls._normalize_path_static(
                    str(section.path), str(content_dir)
                )

            all_section_paths.append(section_path)

            # Get cascade from index page metadata first (preferred)
            # Fall back to section.metadata["cascade"] for backward compatibility
            cascade = {}
            if section.index_page:
                cascade = section.index_page.metadata.get("cascade", {})
            if not cascade:
                cascade = section.metadata.get("cascade", {})
            if cascade:
                data[section_path] = dict(cascade)  # Copy to ensure immutability

        # Phase 2: Pre-compute merged cascade for each section path
        # Sort paths by depth (parent before child) for proper inheritance
        all_section_paths = sorted(set(all_section_paths), key=lambda p: p.count("/"))

        merged: dict[str, dict[str, Any]] = {}

        # Initialize root merged cascade
        root_data = data.get("", {})
        if root_data or "" in all_section_paths:
            merged[""] = dict(root_data)

        for section_path in all_section_paths:
            if not section_path:
                continue  # Root already handled

            # Start with parent's merged cascade
            parent_path = section_path.rsplit("/", 1)[0] if "/" in section_path else ""
            parent_merged = merged.get(parent_path, merged.get("", {}))

            # Create merged cascade: parent values + local overrides
            section_merged = dict(parent_merged)
            local_cascade = data.get(section_path, {})
            section_merged.update(local_cascade)

            merged[section_path] = section_merged

        return cls(_data=data, _merged=merged, _content_dir=str(content_dir))

    @classmethod
    def empty(cls) -> CascadeSnapshot:
        """
        Create an empty cascade snapshot.

        Useful for tests or sites without any cascade metadata.

        Returns:
            Empty frozen CascadeSnapshot.
        """
        return cls(_data={}, _merged={}, _content_dir="")

    @classmethod
    def from_data(
        cls,
        data: dict[str, dict[str, Any]],
        content_dir: str = "",
    ) -> CascadeSnapshot:
        """
        Create a snapshot from raw cascade data with auto-computed merging.

        This is useful for tests and backward compatibility when you want to
        create a snapshot directly from cascade dictionaries without going
        through the full build() process with Section objects.

        The method automatically computes _merged from _data by processing
        paths in depth order (parent before child).

        Args:
            data: Mapping of section_path (str) to cascade dict.
                  e.g., {"docs": {"type": "doc"}, "docs/guide": {"layout": "sidebar"}}
            content_dir: Content directory path for path normalization.

        Returns:
            CascadeSnapshot with both _data and _merged populated.

        Example:
            >>> snapshot = CascadeSnapshot.from_data({
            ...     "docs": {"type": "doc"},
            ...     "docs/guide": {"layout": "sidebar"},
            ... })
            >>> snapshot.resolve("docs/guide", "type")
            "doc"  # Inherited from "docs"
        """
        # Copy data to ensure immutability
        raw_data = {k: dict(v) for k, v in data.items()}

        # Compute merged cascade for each path
        # Sort paths by depth to ensure parent processed before child
        all_paths = sorted(raw_data.keys(), key=lambda p: p.count("/") if p else -1)

        merged: dict[str, dict[str, Any]] = {}

        # Initialize root merged cascade (empty string key)
        if "" in raw_data:
            merged[""] = dict(raw_data[""])

        for path in all_paths:
            if not path:
                continue  # Root already handled

            # Get parent's merged cascade
            parent_path = path.rsplit("/", 1)[0] if "/" in path else ""
            parent_merged = merged.get(parent_path, merged.get("", {}))

            # Create merged cascade: parent values + local overrides
            path_merged = dict(parent_merged)
            path_merged.update(raw_data.get(path, {}))
            merged[path] = path_merged

        return cls(_data=raw_data, _merged=merged, _content_dir=content_dir)

    def __len__(self) -> int:
        """Return number of sections with cascade data."""
        return len(self._data)

    def __contains__(self, section_path: str) -> bool:
        """Check if a section has cascade data defined."""
        normalized = self._normalize_section_path(section_path)
        return normalized in self._data
