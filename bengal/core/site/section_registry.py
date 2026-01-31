"""
Section registry mixin for Site.

Provides methods for O(1) section lookups by path and URL.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from bengal.core.registry import ContentRegistry
    from bengal.core.section import Section


class SiteSectionRegistryMixin:
    """
    Mixin providing section registry methods for Site.

    Enables O(1) section lookups by path or URL through the ContentRegistry.
    """

    # These attributes are defined on the Site dataclass
    root_path: Path
    sections: list[Section]
    _registry: ContentRegistry | None

    # Note: registry property is defined in the main Site class

    def get_section_by_path(self, path: Path | str) -> Section | None:
        """
        Look up a section by its path (O(1) operation).

        Args:
            path: Section path (absolute, relative to content/, or relative to root)

        Returns:
            Section object if found, None otherwise
        """
        if isinstance(path, str):
            path = Path(path)

        if not path.is_absolute():
            content_relative = self.root_path / "content" / path
            if content_relative.exists():
                path = content_relative
            else:
                root_relative = self.root_path / path
                if root_relative.exists():
                    path = root_relative

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

        Args:
            url: Section relative URL (e.g., "/api/", "/api/core/")

        Returns:
            Section object if found, None otherwise
        """
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
        Must be called after discover_content().
        """
        start = time.time()

        self.registry._sections_by_path.clear()
        self.registry._sections_by_url.clear()

        for section in self.sections:
            self.registry.register_sections_recursive(section)

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
