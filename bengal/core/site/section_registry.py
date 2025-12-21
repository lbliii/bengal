"""
Section registry mixin for Site.

Provides O(1) section lookups by path and URL via registries.

Related Modules:
    - bengal.core.site.core: Main Site dataclass using this mixin
    - bengal.core.section: Section model
"""

from __future__ import annotations

import platform
import time
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from bengal.core.section import Section


class SectionRegistryMixin:
    """
    Mixin providing section registry for O(1) lookups.

    Requires these attributes on the host class:
        - root_path: Path
        - sections: list[Section]
        - _section_registry: dict[Path, Section]
        - _section_url_registry: dict[str, Section]
    """

    # Type hints for mixin attributes (provided by host class)
    root_path: Path
    sections: list[Section]
    _section_registry: dict[Path, Section]
    _section_url_registry: dict[str, Section]

    def _normalize_section_path(self, path: Path) -> Path:
        """
        Normalize a section path for registry lookups.

        Normalization ensures consistent lookups across platforms:
        - Resolves symlinks to canonical paths
        - Makes path relative to content/ directory
        - Lowercases on case-insensitive filesystems (macOS, Windows)

        Args:
            path: Absolute or relative section path

        Returns:
            Normalized path suitable for registry keys

        Examples:
            /site/content/blog → blog
            /site/content/docs/guides → docs/guides
            content/BLOG → blog (on macOS/Windows)
        """
        # Resolve symlinks to canonical path
        resolved = path.resolve()

        # Make relative to content/ directory
        content_dir = (self.root_path / "content").resolve()
        try:
            relative = resolved.relative_to(content_dir)
        except ValueError:
            # Path not under content/, use as-is
            relative = resolved

        # Lowercase on case-insensitive filesystems (macOS, Windows)
        system = platform.system()
        if system in ("Darwin", "Windows"):
            # Convert to lowercase string then back to Path
            relative = Path(str(relative).lower())

        return relative

    def get_section_by_path(self, path: Path | str) -> Section | None:
        """
        Look up a section by its path (O(1) operation).

        Uses the section registry for fast lookups without scanning the section tree.
        Paths are normalized before lookup to handle case-insensitive filesystems
        and symlinks consistently.

        Args:
            path: Section path (absolute, relative to content/, or relative to root)

        Returns:
            Section object if found, None otherwise

        Examples:
            >>> section = site.get_section_by_path("blog")
            >>> section = site.get_section_by_path("docs/guides")
            >>> section = site.get_section_by_path(Path("/site/content/blog"))

        Performance:
            O(1) lookup after registry is built (via register_sections)
        """
        if isinstance(path, str):
            path = Path(path)

        # Handle relative paths that might be relative to root_path
        if not path.is_absolute():
            # Try as relative to content/ first
            content_relative = self.root_path / "content" / path
            if content_relative.exists():
                path = content_relative
            else:
                # Try as relative to root_path
                root_relative = self.root_path / path
                if root_relative.exists():
                    path = root_relative

        normalized = self._normalize_section_path(path)
        section = self._section_registry.get(normalized)

        if section is None:
            emit_diagnostic(
                self,
                "debug",
                "section_not_found_in_registry",
                path=str(path),
                normalized=str(normalized),
                registry_size=len(self._section_registry),
            )

        return section

    def get_section_by_url(self, url: str) -> Section | None:
        """
        Look up a section by its relative URL (O(1) operation).

        Used for virtual sections that don't have a disk path. Virtual sections
        are registered by their relative_url during register_sections().

        Args:
            url: Section relative URL (e.g., "/api/", "/api/core/")

        Returns:
            Section object if found, None otherwise

        Examples:
            >>> section = site.get_section_by_url("/api/")
            >>> section = site.get_section_by_url("/api/core/")

        Performance:
            O(1) lookup after registry is built (via register_sections)

        See Also:
            plan/active/rfc-page-section-reference-contract.md
        """
        section = self._section_url_registry.get(url)

        if section is None:
            emit_diagnostic(
                self,
                "debug",
                "section_not_found_in_url_registry",
                url=url,
                registry_size=len(self._section_url_registry),
            )

        return section

    def register_sections(self) -> None:
        """
        Build the section registries for path-based and URL-based lookups.

        Scans all sections recursively and populates:
        - _section_registry: normalized path → Section mappings
        - _section_url_registry: relative_url → Section mappings (for virtual sections)

        This enables O(1) section lookups without scanning the section hierarchy.

        Must be called after discover_content() and before any code that uses
        get_section_by_path(), get_section_by_url(), or page._section property.

        Build ordering invariant:
            1. discover_content()       → Creates Page/Section objects
            2. register_sections()      → Builds registries (THIS)
            3. setup_page_references()  → Sets page._section via property setter
            4. apply_cascades()         → Lookups resolve via registry
            5. generate_urls()          → Uses correct section hierarchy

        Performance:
            O(n) where n = number of sections. Typical: < 10ms for 1000 sections.

        Examples:
            >>> site.discover_content()
            >>> site.register_sections()  # Build registries
            >>> section = site.get_section_by_path("blog")  # O(1) lookup
            >>> virtual_section = site.get_section_by_url("/api/")  # O(1) lookup

        See Also:
            plan/active/rfc-page-section-reference-contract.md
        """
        start = time.time()
        self._section_registry = {}
        self._section_url_registry = {}

        # Register all sections recursively
        for section in self.sections:
            self._register_section_recursive(section)

        elapsed_ms = (time.time() - start) * 1000
        total_registered = len(self._section_registry) + len(self._section_url_registry)

        emit_diagnostic(
            self,
            "debug",
            "section_registry_built",
            path_sections=len(self._section_registry),
            url_sections=len(self._section_url_registry),
            total_registered=total_registered,
            elapsed_ms=f"{elapsed_ms:.2f}",
            avg_us_per_section=f"{(elapsed_ms * 1000 / total_registered):.2f}"
            if total_registered
            else "0",
        )

    def _register_section_recursive(self, section: Section) -> None:
        """
        Recursively register a section and its subsections in the registries.

        Handles both regular sections (with path) and virtual sections (path=None).

        Regular sections: Registered in _section_registry by normalized path.
        Virtual sections: Registered in _section_url_registry by relative_url,
                         enabling page._section lookups via get_section_by_url().

        Args:
            section: Section to register (along with all its subsections)

        See Also:
            plan/active/rfc-page-section-reference-contract.md
        """
        # Handle virtual sections (path is None)
        if section.path is None:
            # Register in URL registry for virtual section lookups
            rel_url = getattr(section, "_path", None) or f"/{section.name}/"
            self._section_url_registry[rel_url] = section

            # Also register in path registry using URL path as key
            rel_url_path = rel_url.strip("/") if rel_url else section.name
            self._section_registry[Path(rel_url_path)] = section

        else:
            # Register regular section by normalized path
            normalized = self._normalize_section_path(section.path)
            self._section_registry[normalized] = section

        # Register subsections recursively
        for subsection in section.subsections:
            self._register_section_recursive(subsection)
