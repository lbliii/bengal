"""
Canonical path representation for all page types.

Eliminates confusion between:
- Source paths (content/about.md)
- Virtual paths (.bengal/generated/tags/python/index.md)
- Output paths (public/about/index.html)
- Internal keys (_generated/tags/tag:python)

Key Concepts:
- Canonical paths: Consistent addressing for cache lookups
- Content vs. generated page distinction
- Cache key generation for BuildCache

Related Modules:
- bengal.cache.build_cache: Uses path registry for consistent keys
- bengal.orchestration.build.coordinator: Uses path registry for page identification
- bengal.cache.paths: BengalPaths for directory locations

See Also:
- plan/rfc-cache-invalidation-architecture.md: Design RFC

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.protocols import PageLike


class PathRegistry:
    """
    Canonical path representation for all page types.

    Eliminates confusion between:
    - Source paths (content/about.md)
    - Virtual paths (.bengal/generated/tags/python/index.md)
    - Output paths (public/about/index.html)
    - Internal keys (_generated/tags/tag:python)

    Cache Key Convention:
        All caches should use canonical_source() as the key for page lookups.
        This ensures consistent addressing regardless of page type.

    Example:
        >>> registry = PathRegistry(site)
        >>> registry.cache_key(page)
        'about.md'  # For content page
        >>> registry.cache_key(generated_page)
        'generated/tags/python/index.md'  # For generated page
    """

    def __init__(self, site: Site) -> None:
        """
        Initialize path registry with site context.

        Args:
            site: Site instance for path resolution
        """
        self.site = site
        self._content_dir = (
            site.paths.content_dir if hasattr(site, "paths") else site.root_path / "content"
        )
        self._generated_dir = (
            site.paths.generated_dir
            if hasattr(site, "paths")
            else site.root_path / ".bengal" / "generated"
        )
        self._output_dir = (
            site.output_dir if hasattr(site, "output_dir") else site.root_path / "public"
        )

    def canonical_source(self, page: PageLike) -> Path:
        """
        Get the canonical source path for any page.

        This is the path used as the key in all caches.

        - Content pages: Relative to content dir (e.g., "about.md")
        - Generated pages: Relative to generated dir with virtual prefix
          (e.g., "generated/tags/python/index.md")
        - Autodoc pages: Relative to source root with virtual prefix
          (e.g., "autodoc/mypackage/core/site.py")

        Args:
            page: Page object to get canonical path for

        Returns:
            Canonical path for use as cache key.
        """
        if page.metadata.get("_generated") or page.metadata.get("is_autodoc"):
            # Virtual page - use virtual prefix for uniqueness in cache
            try:
                # Try to make relative to generated dir if applicable
                rel_path = page.source_path.relative_to(self._generated_dir)
                return Path("generated") / rel_path
            except ValueError:
                # Not in generated dir - use raw source path (e.g. for autodoc sources)
                try:
                    return Path("autodoc") / page.source_path.relative_to(self.site.root_path)
                except ValueError:
                    return page.source_path

        # Content page - use relative path from content dir
        try:
            return page.source_path.relative_to(self._content_dir)
        except ValueError:
            # Fallback: path not under content dir (shouldn't happen)
            return page.source_path

    def cache_key(self, page: PageLike) -> str:
        """
        Get the string cache key for a page.

        Convenience method that converts canonical_source to string.

        Args:
            page: Page object to get cache key for

        Returns:
            String cache key for BuildCache lookups
        """
        return str(self.canonical_source(page))

    def is_generated(self, path: Path) -> bool:
        """
        Check if a path represents a generated page.

        Args:
            path: Path to check

        Returns:
            True if path is in the generated directory
        """
        path_str = str(path)
        generated_str = str(self._generated_dir)
        return path_str.startswith(generated_str) or path_str.startswith(".bengal/generated")

    def virtual_path_for_taxonomy(self, taxonomy: str, term: str) -> Path:
        """
        Get the virtual source path for a taxonomy term page.

        Args:
            taxonomy: Taxonomy name (e.g., "tags")
            term: Term slug (e.g., "python")

        Returns:
            Virtual path like .bengal/generated/tags/python/index.md

        Example:
            >>> registry.virtual_path_for_taxonomy("tags", "python")
            PosixPath('.bengal/generated/tags/python/index.md')
        """
        return self._generated_dir / taxonomy / term / "index.md"

    def output_path(self, page: Page) -> Path:
        """
        Get the output path for a page.

        Args:
            page: Page object to get output path for

        Returns:
            Absolute path to the output HTML file
        """
        url_path = page.url.lstrip("/")
        if url_path.endswith("/"):
            return self._output_dir / url_path / "index.html"
        return self._output_dir / f"{url_path}/index.html"

    def normalize(self, path: Path | str) -> Path:
        """
        Normalize a path to its canonical form.

        Handles both string and Path inputs, resolves relative paths.

        Args:
            path: Path to normalize (string or Path object)

        Returns:
            Normalized absolute Path
        """
        if isinstance(path, str):
            path = Path(path)

        # Remove any leading ./ or resolve relative paths
        if not path.is_absolute():
            path = self.site.root_path / path

        return path.resolve()

    def __repr__(self) -> str:
        """Return string representation."""
        return f"PathRegistry(site={self.site.root_path})"
