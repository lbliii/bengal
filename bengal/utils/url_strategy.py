"""
URL Strategy - Centralized URL and path computation.

This module provides the `URLStrategy` class with pure, stateless utility
functions for computing output paths and URLs throughout the Bengal SSG.
All path computation logic is centralized here to ensure consistency and
prevent path-related bugs across different parts of the system.

Key Features:
    - Output path computation for regular pages, archives, and taxonomy pages
    - Version-aware path transformations for multi-version documentation
    - i18n-aware URL prefixing for multilingual sites
    - Virtual path generation for dynamically generated pages (archives, tags)
    - URL generation from output paths with pretty URL support

Design Principles:
    - **Pure Functions**: No side effects, no state mutation
    - **No Global State**: All inputs passed explicitly via parameters
    - **Easy Testing**: Static methods can be tested in isolation
    - **Reusable**: Used by render orchestrator, taxonomy builder, etc.

Usage:
    >>> from bengal.utils.url_strategy import URLStrategy
    >>> output_path = URLStrategy.compute_regular_page_output_path(page, site)
    >>> url = URLStrategy.url_from_output_path(output_path, site)

Related:
    - `bengal.orchestration.render_orchestrator`: Uses for output path computation
    - `bengal.core.page`: Page objects passed to compute methods
    - `bengal.core.site`: Site object provides configuration and output directory
    - `bengal.utils.url_normalization`: URL validation and normalization utilities
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site


class URLStrategy:
    """
    Pure utility for URL and output path computation.

    Centralizes all path/URL logic to ensure consistency and prevent bugs.
    All methods are static - no state, pure logic.

    Design Principles:
        - Pure functions (no side effects)
        - No dependencies on global state
        - Easy to test in isolation
        - Reusable across orchestrators

    Usage:
        >>> from bengal.utils.url_strategy import URLStrategy
        >>> # Compute output path for a page
        >>> output_path = URLStrategy.compute_regular_page_output_path(page, site)
        >>> # PosixPath('/path/to/site/public/docs/guide/index.html')

        >>> # Generate URL from output path
        >>> url = URLStrategy.url_from_output_path(output_path, site)
        >>> # '/docs/guide/'

        >>> # Compute archive page path
        >>> archive_path = URLStrategy.compute_archive_output_path(section, page_num=1, site=site)
        >>> # PosixPath('/path/to/site/public/blog/index.html')

    See Also:
        - `compute_regular_page_output_path`: For regular content pages
        - `compute_archive_output_path`: For section archive pages
        - `compute_tag_output_path`: For tag listing pages
        - `url_from_output_path`: For generating URLs from paths
        - `make_virtual_path`: For generated/virtual pages
    """

    @staticmethod
    def compute_regular_page_output_path(page: Page, site: Site, pre_cascade: bool = False) -> Path:
        """
        Compute output path for a regular content page.

        Transforms a page's source path into its corresponding output path,
        applying pretty URL rules, version prefixes, and i18n path strategies.

        Args:
            page: Page object with `source_path` attribute set.
            site: Site object providing `output_dir`, `config`, and version info.
            pre_cascade: If True, use the raw source path without any modifications
                         from frontmatter cascade. Used during early page discovery
                         before cascade values are applied. Defaults to False.

        Returns:
            Absolute Path where the page HTML should be written.

        Examples:
            Pretty URLs (default):
                content/about.md → public/about/index.html
                content/blog/post.md → public/blog/post/index.html
                content/docs/_index.md → public/docs/index.html

            Flat URLs (pretty_urls=False):
                content/about.md → public/about.html

            Version-aware:
                content/docs/guide.md (latest) → public/docs/guide/index.html
                _versions/v2/docs/guide.md → public/docs/v2/guide/index.html

            i18n prefix strategy:
                content/about.md (lang=fr) → public/fr/about/index.html
        """
        content_dir = site.root_path / "content"
        pretty_urls = site.config.get("pretty_urls", True)
        # i18n configuration (optional)
        i18n = site.config.get("i18n", {}) or {}
        strategy = i18n.get("strategy", "none")
        default_lang = i18n.get("default_language", "en")
        default_in_subdir = bool(i18n.get("default_in_subdir", False))

        # Get relative path from content directory
        try:
            rel_path = page.source_path.relative_to(content_dir)
        except ValueError:
            # Not under content_dir (shouldn't happen for regular pages)
            rel_path = Path(page.source_path.name)

        if pre_cascade:
            # For pre-cascade, use source_path as-is without modifications
            rel_path = page.source_path.relative_to(content_dir)

        # Handle versioned content paths
        # _versions/v2/docs/guide.md → docs/v2/guide.md
        rel_path = URLStrategy._apply_version_path_transform(rel_path, page, site)

        # Change extension to .html
        output_rel_path = rel_path.with_suffix(".html")

        # Apply URL rules
        if pretty_urls:
            if output_rel_path.stem in ("index", "_index"):
                # _index.md → index.html (keep in same directory)
                output_rel_path = output_rel_path.parent / "index.html"
            else:
                # about.md → about/index.html (directory structure)
                output_rel_path = output_rel_path.parent / output_rel_path.stem / "index.html"
        # Flat URLs: about.md → about.html
        elif output_rel_path.stem == "_index":
            output_rel_path = output_rel_path.parent / "index.html"

        # Apply i18n URL strategy (prefix)
        if strategy == "prefix":
            lang: str | None = getattr(page, "lang", None)
            # If default language should be under subdir or non-default language: prefix
            if lang and (default_in_subdir or lang != default_lang):
                output_rel_path = Path(lang) / output_rel_path
        # strategy 'domain' or 'none' → no path prefixing here
        return site.output_dir / output_rel_path

    @staticmethod
    def _apply_version_path_transform(rel_path: Path, page: Page, site: Site) -> Path:
        """
        Transform versioned content path to output path structure.

        For non-latest versions, inserts version prefix after the section:
        - _versions/v2/docs/guide.md → docs/v2/guide.md
        - _versions/v1/docs/api/ref.md → docs/v1/api/ref.md

        For latest version or non-versioned content:
        - docs/guide.md → docs/guide.md (unchanged)

        Args:
            rel_path: Relative path from content directory
            page: Page object (for version info)
            site: Site object (for version config)

        Returns:
            Transformed path with version prefix if applicable
        """
        # Fast path: skip if versioning is disabled (most sites)
        if not getattr(site, "versioning_enabled", False):
            return rel_path

        # Get page's version
        page_version = getattr(page, "version", None)
        if not page_version:
            return rel_path

        # Get version config (we know it's enabled now)
        version_config = site.version_config

        # Check if this is the latest version (no prefix needed)
        version_obj = version_config.get_version(page_version)
        if not version_obj or version_obj.latest:
            # Latest version: strip _versions/<id>/ prefix if present
            parts = rel_path.parts
            if len(parts) >= 2 and parts[0] == "_versions":
                # _versions/v3/docs/guide.md → docs/guide.md
                if len(parts) > 2:
                    return Path(*parts[2:])
                # Path is just _versions/<id>/; nothing to strip into a content path
                return rel_path
            return rel_path

        # Non-latest version: insert version prefix after section
        parts = rel_path.parts

        # Check if path starts with _versions/<id>/
        if len(parts) >= 2 and parts[0] == "_versions":
            # _versions/v2/docs/guide.md → docs/v2/guide.md
            version_id = parts[1]
            section_and_rest = parts[2:]  # docs/guide.md

            if section_and_rest:
                section = section_and_rest[0]  # docs
                rest = section_and_rest[1:]  # guide.md

                # Insert version after section: docs/v2/guide.md
                if rest:
                    return Path(section) / version_id / Path(*rest)
                return Path(section) / version_id
            else:
                # Just _versions/v2/ → v2/
                return Path(version_id)

        # Content is in main content directory but has version set
        # (shouldn't normally happen, but handle gracefully)
        return rel_path

    @staticmethod
    def compute_archive_output_path(section: Section, page_num: int, site: Site) -> Path:
        """
        Compute output path for a section archive page.

        Args:
            section: Section to create archive for
            page_num: Page number (1 for first page, 2+ for pagination)
            site: Site object (for output_dir)

        Returns:
            Absolute path where the archive HTML should be written

        Examples:
            section='docs', page=1 → public/docs/index.html
            section='docs', page=2 → public/docs/page/2/index.html
            section='docs/markdown', page=1 → public/docs/markdown/index.html
        """
        # Get full hierarchy (excluding 'root')
        hierarchy = [h for h in section.hierarchy if h != "root"]

        # Build base path
        path = site.output_dir
        for segment in hierarchy:
            path = path / segment

        # Add pagination if needed
        if page_num > 1:
            path = path / "page" / str(page_num)

        return path / "index.html"

    @staticmethod
    def compute_tag_output_path(tag_slug: str, page_num: int, site: Site) -> Path:
        """
        Compute output path for a tag listing page.

        Args:
            tag_slug: URL-safe tag identifier
            page_num: Page number (1 for first page, 2+ for pagination)
            site: Site object (for output_dir)

        Returns:
            Absolute path where the tag page HTML should be written

        Examples:
            tag='python', page=1 → public/tags/python/index.html
            tag='python', page=2 → public/tags/python/page/2/index.html
        """
        # i18n prefix support using site's current language context
        i18n = site.config.get("i18n", {}) or {}
        strategy = i18n.get("strategy", "none")
        default_lang = i18n.get("default_language", "en")
        default_in_subdir = bool(i18n.get("default_in_subdir", False))
        lang = getattr(site, "current_language", None)

        base_path = site.output_dir
        if strategy == "prefix" and lang and (default_in_subdir or lang != default_lang):
            base_path = base_path / lang

        path = base_path / "tags" / tag_slug

        # Add pagination if needed
        if page_num > 1:
            path = path / "page" / str(page_num)

        return path / "index.html"

    @staticmethod
    def compute_tag_index_output_path(site: Site) -> Path:
        """
        Compute output path for the main tags index page.

        Args:
            site: Site object (for output_dir)

        Returns:
            Absolute path where the tags index HTML should be written

        Example:
            public/tags/index.html
        """
        # i18n prefix support using site's current language context
        i18n = site.config.get("i18n", {}) or {}
        strategy = i18n.get("strategy", "none")
        default_lang = i18n.get("default_language", "en")
        default_in_subdir = bool(i18n.get("default_in_subdir", False))
        lang = getattr(site, "current_language", None)

        base_path = site.output_dir
        if strategy == "prefix" and lang and (default_in_subdir or lang != default_lang):
            base_path = base_path / lang

        return base_path / "tags" / "index.html"

    @staticmethod
    def url_from_output_path(output_path: Path, site: Site) -> str:
        """
        Generate clean URL from output path.

        Args:
            output_path: Absolute path to output file
            site: Site object (for output_dir)

        Returns:
            Clean URL with leading/trailing slashes

        Examples:
            public/about/index.html → /about/
            public/docs/guide.html → /docs/guide/
            public/index.html → /

        Raises:
            ValueError: If output_path is not under site.output_dir
        """
        try:
            rel_path = output_path.relative_to(site.output_dir)
        except ValueError:
            from bengal.errors import BengalContentError

            raise BengalContentError(
                f"Output path {output_path} is not under output directory {site.output_dir}",
                suggestion="Ensure output paths are within the site's output directory",
            ) from None

        # Convert to URL parts
        url_parts = list(rel_path.parts)

        # Remove index.html (implicit in URLs)
        if url_parts and url_parts[-1] == "index.html":
            url_parts = url_parts[:-1]
        elif url_parts and url_parts[-1].endswith(".html"):
            # Non-index: remove .html extension
            url_parts[-1] = url_parts[-1][:-5]

        # Build URL
        if not url_parts:
            return "/"

        url = "/" + "/".join(url_parts)

        # Ensure trailing slash
        if not url.endswith("/"):
            url += "/"

        return url

    @staticmethod
    def make_virtual_path(site: Site, *parts: str) -> Path:
        """
        Create virtual source path for generated pages.

        Generated pages (archives, tags, etc.) don't have real source files.
        This creates a virtual path under .bengal/generated/ for tracking.

        Args:
            site: Site object (for root_path)
            *parts: Path components

        Returns:
            Virtual path under .bengal/generated/

        Examples:
            make_virtual_path(site, 'archives', 'docs')
            → /path/to/site/.bengal/generated/archives/docs/index.md

            make_virtual_path(site, 'tags', 'python')
            → /path/to/site/.bengal/generated/tags/python/index.md
        """
        return site.paths.generated_dir / Path(*parts) / "index.md"
