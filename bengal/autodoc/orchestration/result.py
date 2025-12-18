"""
Autodoc run result and page context classes.

Provides:
    - AutodocRunResult: Summary of an autodoc generation run
    - PageContext: Lightweight page-like context for template rendering
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.section import Section


@dataclass
class AutodocRunResult:
    """
    Summary of an autodoc generation run.

    Tracks successes, failures, and warnings for observability and strict mode enforcement.

    Attributes:
        extracted: Number of elements successfully extracted
        rendered: Number of pages successfully rendered
        failed_extract: Number of extraction failures
        failed_render: Number of rendering failures
        warnings: Number of warnings emitted
        failed_extract_identifiers: Qualified names of elements that failed extraction
        failed_render_identifiers: Qualified names of elements that failed rendering
        fallback_pages: URL paths of pages rendered via fallback template
        autodoc_dependencies: Mapping of source file paths to autodoc page paths
    """

    extracted: int = 0
    """Number of elements successfully extracted."""
    rendered: int = 0
    """Number of pages successfully rendered."""
    failed_extract: int = 0
    """Number of extraction failures."""
    failed_render: int = 0
    """Number of rendering failures."""
    warnings: int = 0
    """Number of warnings emitted."""
    failed_extract_identifiers: list[str] = field(default_factory=list)
    """Qualified names of elements that failed extraction."""
    failed_render_identifiers: list[str] = field(default_factory=list)
    """Qualified names of elements that failed rendering."""
    fallback_pages: list[str] = field(default_factory=list)
    """URL paths of pages rendered via fallback template."""
    autodoc_dependencies: dict[str, set[str]] = field(default_factory=dict)
    """Mapping of source file paths to the autodoc page paths they produce.
    Used by IncrementalOrchestrator for selective autodoc rebuilds."""

    def has_failures(self) -> bool:
        """Check if any failures occurred."""
        return self.failed_extract > 0 or self.failed_render > 0

    def has_warnings(self) -> bool:
        """Check if any warnings occurred."""
        return self.warnings > 0

    def add_dependency(self, source_file: str, page_path: str) -> None:
        """
        Register a dependency between a source file and an autodoc page.

        Args:
            source_file: Path to the Python/OpenAPI source file
            page_path: Path to the generated autodoc page (source_path)
        """
        if source_file not in self.autodoc_dependencies:
            self.autodoc_dependencies[source_file] = set()
        self.autodoc_dependencies[source_file].add(page_path)


class PageContext:
    """
    Lightweight page-like context for autodoc template rendering.

    Templates extend base.html and include partials that expect a 'page' variable
    with attributes like metadata, tags, title, and relative_url. This class provides
    those attributes without requiring a full Page object (which doesn't exist yet
    during the initial render phase).

    The navigation attributes (prev, next, prev_in_section, next_in_section) are
    set to None since autodoc virtual pages don't participate in linear navigation.

    Attributes:
        title: Page title
        metadata: Page metadata dict
        tags: List of tags
        relative_url: Relative URL path
        variant: Optional variant name
        source_path: Optional source file path
        section: Optional parent section
    """

    def __init__(
        self,
        title: str,
        metadata: dict[str, Any],
        tags: list[str] | None = None,
        relative_url: str = "/",
        variant: str | None = None,
        source_path: str | None = None,
        section: Section | None = None,
    ) -> None:
        self.title = title
        self.metadata = metadata
        self.tags = tags or []
        self.relative_url = relative_url
        self.variant = variant
        self.source_path = source_path

        # Navigation attributes (None = autodoc pages don't have linear navigation)
        self.prev: PageContext | None = None
        self.next: PageContext | None = None
        self.prev_in_section: PageContext | None = None
        self.next_in_section: PageContext | None = None

        # Section reference (used by docs-nav.html for sidebar navigation)
        # Templates check page._section, so we need both aliases
        self._section = section
        self.section = section

    def __repr__(self) -> str:
        return f"PageContext(title={self.title!r}, relative_url={self.relative_url!r})"


# Backward compatibility alias
_PageContext = PageContext
