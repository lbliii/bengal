"""
Content Registry - O(1) content lookups by path and URL.

Provides ContentRegistry for centralized page/section lookups with path and URL
indexing. Enables efficient access to content during rendering without scanning
hierarchies.

Public API:
    ContentRegistry: Central registry for page and section lookups

Key Concepts:
    Path-Based Lookups: O(1) access by source file path (primary key)
    URL-Based Lookups: O(1) access by output URL (for virtual content and links)
    Freeze/Unfreeze: Registry frozen after discovery for thread-safe reads

Lifecycle:
    1. Created empty at Site initialization
    2. Populated during discovery phase (register_page/register_section)
    3. Frozen before rendering phase (freeze())
    4. Cleared on rebuild (clear())

Thread Safety:
    - Writes (register_*) must happen single-threaded during discovery
    - Reads (get_*) are safe after freeze() for concurrent rendering
    - Frozen registry raises RuntimeError on mutation attempts

Related Packages:
    bengal.core.site.core: Site dataclass using this registry
    bengal.core.url_ownership: URL ownership tracking (composed by registry)
    bengal.core.site.section_registry: Legacy mixin (delegates to registry)
"""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.core.url_ownership import URLRegistry

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section


@dataclass
class ContentRegistry:
    """
    O(1) content lookups by path, URL, and metadata.

    Thread-safe for reads after freeze(). Rebuilt atomically during discovery.

    Lifecycle:
        1. Created empty at Site initialization
        2. Populated during discovery phase (register_page/register_section)
        3. Frozen before rendering phase (freeze())
        4. Cleared on rebuild (clear())

    Thread Safety:
        - Writes (register_*) must happen single-threaded during discovery
        - Reads (get_*) are safe after freeze() for concurrent rendering
        - Frozen registry raises RuntimeError on mutation attempts

    Attributes:
        url_ownership: URLRegistry for collision detection and ownership tracking
    """

    # Path-based lookups (primary keys)
    _pages_by_path: dict[Path, Page] = field(default_factory=dict)
    _sections_by_path: dict[Path, Section] = field(default_factory=dict)

    # URL-based lookups (for virtual content and link resolution)
    _pages_by_url: dict[str, Page] = field(default_factory=dict)
    _sections_by_url: dict[str, Section] = field(default_factory=dict)

    # URL ownership (for collision detection)
    url_ownership: URLRegistry = field(default_factory=URLRegistry)

    # Root path for path normalization (set by Site)
    _root_path: Path | None = field(default=None, repr=False)

    # Frozen flag (set after discovery, before rendering)
    _frozen: bool = field(default=False, repr=False)

    # Epoch counter for cache invalidation (incremented on clear/re-registration)
    # Used by Page._section to detect when section cache is stale
    _epoch: int = field(default=0, repr=False)

    def get_page(self, path: Path) -> Page | None:
        """
        Get page by source path. O(1) lookup.

        Args:
            path: Source file path (absolute or relative to content/)

        Returns:
            Page if found, None otherwise
        """
        # Try direct lookup first
        page = self._pages_by_path.get(path)
        if page is not None:
            return page

        # Try normalized path
        if self._root_path is not None:
            normalized = self._normalize_path(path)
            return self._pages_by_path.get(normalized)

        return None

    def get_page_by_url(self, url: str) -> Page | None:
        """
        Get page by output URL. O(1) lookup.

        Args:
            url: Output URL (e.g., "/about/", "/blog/my-post/")

        Returns:
            Page if found, None otherwise
        """
        return self._pages_by_url.get(url)

    def get_section(self, path: Path) -> Section | None:
        """
        Get section by directory path. O(1) lookup.

        Args:
            path: Section directory path (absolute or relative to content/)

        Returns:
            Section if found, None otherwise
        """
        # Try direct lookup first
        section = self._sections_by_path.get(path)
        if section is not None:
            return section

        # Try normalized path
        if self._root_path is not None:
            normalized = self._normalize_path(path)
            return self._sections_by_path.get(normalized)

        return None

    def get_section_by_url(self, url: str) -> Section | None:
        """
        Get section by URL (for virtual sections). O(1) lookup.

        Args:
            url: Section URL (e.g., "/api/", "/api/core/")

        Returns:
            Section if found, None otherwise
        """
        return self._sections_by_url.get(url)

    def register_page(self, page: Page) -> None:
        """
        Register a page. Raises if frozen.

        Args:
            page: Page to register (must have source_path set)

        Raises:
            RuntimeError: If registry is frozen
        """
        if self._frozen:
            raise RuntimeError("Cannot modify frozen registry")

        # Register by source path
        if page.source_path:
            normalized = self._normalize_path(page.source_path)
            self._pages_by_path[normalized] = page

        # Register by URL
        if page._path:
            self._pages_by_url[page._path] = page

    def register_section(self, section: Section) -> None:
        """
        Register a section. Raises if frozen.

        Args:
            section: Section to register

        Raises:
            RuntimeError: If registry is frozen
        """
        if self._frozen:
            raise RuntimeError("Cannot modify frozen registry")

        # Handle virtual sections (path is None)
        if section.path is None:
            # Register in URL registry for virtual section lookups
            rel_url = getattr(section, "_path", None) or f"/{section.name}/"
            self._sections_by_url[rel_url] = section

            # Also register in path registry using URL path as key
            rel_url_path = rel_url.strip("/") if rel_url else section.name
            self._sections_by_path[Path(rel_url_path)] = section
        else:
            # Register regular section by normalized path
            normalized = self._normalize_path(section.path)
            self._sections_by_path[normalized] = section

    def register_sections_recursive(self, section: Section) -> None:
        """
        Register a section and all its subsections recursively.

        Args:
            section: Root section to register (along with all subsections)

        Raises:
            RuntimeError: If registry is frozen
        """
        self.register_section(section)
        for subsection in section.subsections:
            self.register_sections_recursive(subsection)

    def freeze(self) -> None:
        """
        Freeze registry after discovery. Enables concurrent reads.

        Called at the end of discovery phase, before rendering begins.
        After freezing, any mutation attempt raises RuntimeError.
        """
        self._frozen = True

    def unfreeze(self) -> None:
        """
        Unfreeze registry for dev server rebuilds.

        Called at start of reset_ephemeral_state() to allow re-population.
        """
        self._frozen = False

    def clear(self) -> None:
        """
        Clear all entries for rebuild. Also unfreezes.

        Called by Site.reset_ephemeral_state() before re-discovery.
        Increments epoch to invalidate page section caches.
        """
        self._pages_by_path.clear()
        self._sections_by_path.clear()
        self._pages_by_url.clear()
        self._sections_by_url.clear()
        self.url_ownership = URLRegistry()
        self._frozen = False
        self._epoch += 1

    def set_root_path(self, root_path: Path) -> None:
        """
        Set root path for path normalization.

        Args:
            root_path: Site root directory
        """
        self._root_path = root_path.resolve() if root_path else None

    def _normalize_path(self, path: Path) -> Path:
        """
        Normalize a path for registry lookups.

        Normalization ensures consistent lookups across platforms:
        - Resolves symlinks to canonical paths
        - Makes path relative to content/ directory
        - Lowercases on case-insensitive filesystems (macOS, Windows)

        Args:
            path: Absolute or relative path

        Returns:
            Normalized path suitable for registry keys
        """
        if self._root_path is None:
            return path

        # Resolve symlinks to canonical path
        try:
            resolved = path.resolve()
        except (OSError, ValueError):
            # Path doesn't exist or is invalid, use as-is
            resolved = path

        # Make relative to content/ directory
        content_dir = (self._root_path / "content").resolve()
        try:
            relative = resolved.relative_to(content_dir)
        except ValueError:
            # Path not under content/, try relative to root
            try:
                relative = resolved.relative_to(self._root_path)
            except ValueError:
                # Use as-is
                relative = resolved

        # Lowercase on case-insensitive filesystems (macOS, Windows)
        system = platform.system()
        if system in ("Darwin", "Windows"):
            relative = Path(str(relative).lower())

        return relative

    @property
    def page_count(self) -> int:
        """Number of registered pages."""
        return len(self._pages_by_path)

    @property
    def section_count(self) -> int:
        """Number of registered sections."""
        return len(self._sections_by_path)

    @property
    def is_frozen(self) -> bool:
        """Whether the registry is frozen."""
        return self._frozen

    @property
    def epoch(self) -> int:
        """
        Registry epoch counter for cache invalidation.

        Incremented when clear() is called. Used by Page._section to
        detect when cached section lookups are stale.
        """
        return self._epoch

    def increment_epoch(self) -> None:
        """
        Increment the epoch counter.

        Called after sections are re-registered to invalidate page caches.
        """
        self._epoch += 1

    def __repr__(self) -> str:
        frozen_str = " (frozen)" if self._frozen else ""
        return (
            f"ContentRegistry(pages={self.page_count}, sections={self.section_count}{frozen_str})"
        )
