"""
Autodoc dependency tracking mixin for BuildCache.

Tracks which Python source files produce which autodoc pages, enabling
selective regeneration of autodoc pages when their source files change.

Key Concepts:
    - Source file tracking: Maps Python/OpenAPI source files to autodoc page paths
    - Selective invalidation: Only rebuild affected autodoc pages, not all
    - Orphan cleanup: Remove autodoc pages when source files are deleted

Related Modules:
    - bengal.autodoc.orchestration: Creates autodoc pages with dependencies
    - bengal.orchestration.incremental: Uses dependency info for selective builds

See Also:
    - plan/active/rfc-autodoc-incremental-builds.md: Design rationale
"""

from __future__ import annotations

from dataclasses import field
from pathlib import Path
from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class AutodocTrackingMixin:
    """
    Track autodoc source file to page dependencies.

    This mixin adds dependency tracking for autodoc pages, enabling selective
    rebuilds when only specific Python/OpenAPI source files change.

    Attributes:
        autodoc_dependencies: Mapping of source_file path to set of autodoc page paths
            that are generated from that source file.
    """

    # Mixin expects these to be defined in the main dataclass
    autodoc_dependencies: dict[str, set[str]] = field(default_factory=dict)

    def add_autodoc_dependency(self, source_file: Path | str, autodoc_page: Path | str) -> None:
        """
        Register that source_file produces autodoc_page.

        Args:
            source_file: Path to the Python/OpenAPI source file
            autodoc_page: Path to the generated autodoc page (source_path)
        """
        source_key = str(source_file)
        page_key = str(autodoc_page)

        if source_key not in self.autodoc_dependencies:
            self.autodoc_dependencies[source_key] = set()
        self.autodoc_dependencies[source_key].add(page_key)

        logger.debug(
            "autodoc_dependency_registered",
            source_file=source_key,
            autodoc_page=page_key,
        )

    def get_affected_autodoc_pages(self, changed_source: Path | str) -> set[str]:
        """
        Get autodoc pages affected by a source file change.

        Args:
            changed_source: Path to the changed Python/OpenAPI source file

        Returns:
            Set of autodoc page paths that need to be rebuilt
        """
        source_key = str(changed_source)
        return self.autodoc_dependencies.get(source_key, set())

    def get_autodoc_source_files(self) -> set[str]:
        """
        Get all tracked autodoc source files.

        Returns:
            Set of all source file paths that have autodoc dependencies
        """
        return set(self.autodoc_dependencies.keys())

    def clear_autodoc_dependencies(self) -> None:
        """
        Clear all autodoc dependency mappings.

        Called when autodoc configuration changes to ensure fresh mappings.
        """
        self.autodoc_dependencies.clear()
        logger.debug("autodoc_dependencies_cleared")

    def remove_autodoc_source(self, source_file: Path | str) -> set[str]:
        """
        Remove a source file and return its associated autodoc pages.

        Args:
            source_file: Path to the source file being removed

        Returns:
            Set of autodoc page paths that were associated with this source
        """
        source_key = str(source_file)
        removed_pages = self.autodoc_dependencies.pop(source_key, set())

        if removed_pages:
            logger.debug(
                "autodoc_source_removed",
                source_file=source_key,
                affected_pages=len(removed_pages),
            )

        return removed_pages

    def get_autodoc_stats(self) -> dict[str, Any]:
        """
        Get statistics about autodoc dependency tracking.

        Returns:
            Dictionary with tracking stats
        """
        total_sources = len(self.autodoc_dependencies)
        total_pages = sum(len(pages) for pages in self.autodoc_dependencies.values())

        return {
            "autodoc_source_files": total_sources,
            "autodoc_pages_tracked": total_pages,
        }
