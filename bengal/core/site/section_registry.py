"""
Section registry mixin for Site.

Provides O(1) section lookups by path and URL via ContentRegistry.

See: plan/drafted/rfc-site-responsibility-separation.md

Related Modules:
    - bengal.core.site.core: Main Site dataclass using this mixin
    - bengal.core.section: Section model
    - bengal.core.registry: ContentRegistry for centralized lookups
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from bengal.core.section import Section


class SectionRegistryMixin:
    """
    Mixin providing section registry for O(1) lookups.

    Delegates to ContentRegistry for all lookups.

    Requires these attributes on the host class:
        - root_path: Path
        - sections: list[Section]
        - registry: ContentRegistry (property)
    """

    # Type hints for mixin attributes (provided by host class)
    root_path: Path
    sections: list[Section]

    # Registry property (provided by Site)
    @property
    def registry(self) -> Any:  # Returns ContentRegistry, using Any to avoid import cycle
        """Override in Site class."""
        raise NotImplementedError

    def get_section_by_path(self, path: Path | str) -> Section | None:
        """
        Look up a section by its path (O(1) operation).

        Delegates to ContentRegistry for fast lookups without scanning the section tree.

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

        # Delegate to ContentRegistry
        section = self.registry.get_section(path)

        if section is None:
            emit_diagnostic(
                self,
                "debug",
                "section_not_found_in_registry",
                path=str(path),
                registry_size=self.registry.section_count,
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
        # Delegate to ContentRegistry
        section = self.registry.get_section_by_url(url)

        if section is None:
            emit_diagnostic(
                self,
                "debug",
                "section_not_found_in_url_registry",
                url=url,
                registry_size=self.registry.section_count,
            )

        return section

    def register_sections(self) -> None:
        """
        Build the section registry for path-based and URL-based lookups.

        Populates ContentRegistry with all sections (recursive).

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
            plan/drafted/rfc-site-responsibility-separation.md
        """
        start = time.time()

        # Clear ContentRegistry section entries for fresh registration
        # This ensures re-registration picks up new Section objects
        self.registry._sections_by_path.clear()
        self.registry._sections_by_url.clear()

        # Register all sections recursively
        for section in self.sections:
            self.registry.register_sections_recursive(section)

        # Increment epoch to invalidate page section caches
        # This ensures Page._section lookups see the new Section objects
        self.registry.increment_epoch()

        elapsed_ms = (time.time() - start) * 1000

        emit_diagnostic(
            self,
            "debug",
            "section_registry_built",
            sections=self.registry.section_count,
            elapsed_ms=f"{elapsed_ms:.2f}",
            avg_us_per_section=f"{(elapsed_ms * 1000 / self.registry.section_count):.2f}"
            if self.registry.section_count
            else "0",
        )
