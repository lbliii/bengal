"""
Link validation for catching broken links.

This module provides the single source of truth for link validation in Bengal.
It validates internal links in pages against the site's page URLs to catch
broken links during build time.

Key features:
- Validates internal links resolve to existing pages
- Handles relative paths and fragments
- Supports trailing slash variations
- Caches validation results for performance
- Integrates with health check system for observability

Architecture:
    This module consolidates link validation that was previously split between
    rendering/ and health/. The LinkValidator class contains the core logic,
    while LinkValidatorWrapper integrates it into the health check framework.

Related:
    - bengal/health/validators/__init__.py: Validator exports
    - bengal/core/page/operations.py: Page.validate_links() method
    - plan/ready/plan-architecture-refactoring.md: Sprint 3 consolidation
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, override
from urllib.parse import urljoin, urlparse

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, ValidatorStats
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


class LinkValidator:
    """
    Validates links in pages to catch broken links.

    This validator checks that internal links resolve to existing pages
    in the site. External links (http/https), mailto, tel, and fragment-only
    links are skipped (external link checking is handled separately).

    Attributes:
        validated_urls: Set of URLs that have been validated (cache)
        broken_links: List of (page_path, broken_link) tuples
        _page_urls: Cached set of all page URLs for O(1) lookup
        _source_paths: Cached set of all source paths for resolving relative links
        _site: Reference to site being validated
    """

    def __init__(self, site: Site | None = None) -> None:
        """
        Initialize the link validator.

        Args:
            site: Optional Site instance for URL resolution
        """
        self.validated_urls: set[str] = set()
        self.broken_links: list[tuple[Path | None, str]] = []
        self._page_urls: set[str] | None = None
        self._source_paths: set[str] | None = None
        self._site: Site | None = site

    def _build_page_url_index(self, site: Any) -> set[str]:
        """
        Build an index of all page URLs for fast lookup.

        Creates normalized URL variants (with/without trailing slashes)
        for flexible matching.

        Args:
            site: Site instance containing pages

        Returns:
            Set of all valid page URLs
        """
        urls: set[str] = set()
        for page in site.pages:
            url = getattr(page, "href", None)
            if url:
                # Add both with and without trailing slash for flexible matching
                urls.add(url)
                urls.add(url.rstrip("/"))
                urls.add(url.rstrip("/") + "/")

                # Also add permalink if different
                permalink = getattr(page, "permalink", None)
                if permalink and permalink != url:
                    urls.add(permalink)
                    urls.add(permalink.rstrip("/"))
                    urls.add(permalink.rstrip("/") + "/")

        return urls

    def _build_source_path_index(self, site: Any) -> set[str]:
        """
        Build an index of all source paths for resolving relative links.

        Used to validate relative links like ./sibling.md against actual source files.

        Args:
            site: Site instance containing pages

        Returns:
            Set of all source paths (normalized, relative to content dir)
        """
        paths: set[str] = set()
        content_root = getattr(site, "content_dir", None) or (site.root_path / "content")

        for page in site.pages:
            source_path = getattr(page, "source_path", None)
            if source_path:
                # Add the full path
                paths.add(str(source_path))
                # Try to add path relative to content root
                try:
                    rel_path = Path(source_path).relative_to(content_root)
                    paths.add(str(rel_path))
                except ValueError:
                    pass

        return paths

    def validate_page_links(self, page: Page, site: Any | None = None) -> list[str]:
        """
        Validate all links in a page.

        Args:
            page: Page to validate
            site: Optional Site instance (uses cached if not provided)

        Returns:
            List of broken link URLs
        """
        # Use provided site or cached site
        site = site or self._site

        # Build indexes on first use (or if site changed)
        if self._page_urls is None and site is not None:
            self._page_urls = self._build_page_url_index(site)
            self._source_paths = self._build_source_path_index(site)
            self._site = site

        logger.debug(
            "validating_page_links", page=str(page.source_path), link_count=len(page.links)
        )

        broken = []

        for link in page.links:
            if not self._is_valid_link(link, page):
                broken.append(link)
                self.broken_links.append((page.source_path, link))

        if broken:
            logger.debug(
                "found_broken_links_in_page",
                page=str(page.source_path),
                broken_count=len(broken),
                broken_links=broken[:5],
            )

        return broken

    def validate_site(self, site: Any) -> list[tuple[Path | None, str]]:
        """
        Validate all links in the entire site.

        Args:
            site: Site instance

        Returns:
            List of (page_path, broken_link) tuples
        """
        logger.debug("validating_site_links", page_count=len(site.pages))

        # Reset state
        self.broken_links = []
        self._site = site
        self._page_urls = self._build_page_url_index(site)
        self._source_paths = self._build_source_path_index(site)

        for page in site.pages:
            self.validate_page_links(page, site)

        if self.broken_links:
            pages_affected = len(set(str(page_path) for page_path, _ in self.broken_links))

            def _relative_path(path: Path | str) -> str:
                """Convert to project-relative path for display."""
                try:
                    return str(Path(path).relative_to(site.root_path))
                except ValueError:
                    return str(path)

            logger.warning(
                "found_broken_links",
                total_broken=len(self.broken_links),
                pages_affected=pages_affected,
                sample_links=[(_relative_path(p), link) for p, link in self.broken_links[:10]],
            )
        else:
            logger.debug(
                "link_validation_complete",
                total_links_checked=len(self.validated_urls),
                broken_links=0,
            )

        return self.broken_links

    def _is_valid_link(self, link: str, page: Page) -> bool:
        """
        Check if a link is valid.

        Validates internal links by:
        1. Resolving relative paths against page URL
        2. Checking if target exists in page URL index
        3. Handling fragment-only links

        Args:
            link: Link URL to check
            page: Page containing the link

        Returns:
            True if link is valid, False otherwise
        """
        # Skip external links (http/https) - validated separately by async link checker
        if link.startswith(("http://", "https://", "mailto:", "tel:")):
            logger.debug(
                "skipping_external_link",
                link=link[:100],
                type="external" if link.startswith("http") else "special",
            )
            self.validated_urls.add(link)
            return True

        # Skip data URLs
        if link.startswith("data:"):
            self.validated_urls.add(link)
            return True

        # Skip template syntax (Jinja2, JavaScript template literals, etc.)
        # These appear in documentation code examples and are not real links
        if "{{" in link or "}}" in link or "${" in link:
            logger.debug(
                "skipping_template_syntax",
                link=link[:100],
                reason="template_syntax_in_code_example",
            )
            self.validated_urls.add(link)
            return True

        # Skip source file references (common in autodoc-generated content)
        # These are "View Source" links that point to Python files, not doc pages
        # Patterns: bengal/module.py#L1, ../module.py, path/to/file.py
        if ".py" in link and (
            link.endswith(".py") or ".py#" in link  # Python file with fragment (line number)
        ):
            logger.debug(
                "skipping_source_file_reference",
                link=link[:100],
                reason="source_file_reference_in_autodoc",
            )
            self.validated_urls.add(link)
            return True

        # Parse the link
        parsed = urlparse(link)

        # Fragment-only links (e.g., "#section") are valid within the page
        if not parsed.path and parsed.fragment:
            logger.debug(
                "validating_fragment_link",
                link=link,
                page=str(page.source_path),
                result="valid",
            )
            self.validated_urls.add(link)
            return True

        # Skip if we have no page URL index (graceful degradation)
        if self._page_urls is None:
            logger.debug(
                "link_validation_skipped",
                link=link,
                reason="no_page_url_index",
            )
            return True

        # Handle relative links to .md files by resolving against source path
        # This handles common patterns like:
        # - [link](./sibling.md)
        # - [link](../other.md)
        # - [link](sibling.md)  (implicit current directory)
        if parsed.path.endswith(".md") and not parsed.path.startswith("/"):
            return self._validate_relative_md_link(parsed.path, page)

        # Get page's URL for resolving other relative links
        page_url = getattr(page, "href", None)
        if not page_url:
            # Can't resolve without page URL
            logger.debug(
                "link_validation_skipped",
                link=link,
                reason="no_page_url",
            )
            return True

        # Ensure page_url is a string (not Path)
        page_url = str(page_url)

        # Resolve relative link against page URL
        # Ensure page_url has trailing slash for proper resolution
        base_url = page_url if page_url.endswith("/") else page_url + "/"
        resolved = urljoin(base_url, str(parsed.path))

        # Strip fragment for URL matching
        resolved_path = resolved.split("#")[0] if "#" in resolved else resolved

        # Normalize .md extensions - users commonly link to .md files which
        # resolve to clean URLs without extensions
        if resolved_path.endswith(".md"):
            # Handle _index.md -> parent directory URL
            if resolved_path.endswith("/_index.md"):
                resolved_path = resolved_path[:-10]  # Strip /_index.md
                if not resolved_path:
                    resolved_path = "/"
            elif resolved_path.endswith("/index.md"):
                resolved_path = resolved_path[:-9]  # Strip /index.md
                if not resolved_path:
                    resolved_path = "/"
            else:
                # Regular .md file -> strip extension
                resolved_path = resolved_path[:-3]

        # Check all normalized variants
        variants = [
            resolved_path,
            resolved_path.rstrip("/"),
            resolved_path.rstrip("/") + "/",
        ]

        # Check if any variant matches a known page URL
        is_valid = any(v in self._page_urls for v in variants)

        if is_valid:
            logger.debug(
                "validating_internal_link",
                link=link,
                resolved=resolved_path,
                page=str(page.source_path),
                result="valid",
            )
            self.validated_urls.add(link)
        else:
            logger.debug(
                "validating_internal_link",
                link=link,
                resolved=resolved_path,
                page=str(page.source_path),
                result="broken",
                checked_variants=variants[:3],
            )

        return is_valid

    def _validate_relative_md_link(self, link_path: str, page: Page) -> bool:
        """
        Validate a relative link to a .md file by resolving against source path.

        This handles common markdown patterns like:
        - [sibling](./sibling.md)
        - [parent](../parent.md)
        - [index](./_index.md)

        Args:
            link_path: The relative path (e.g., "./sibling.md")
            page: The page containing the link

        Returns:
            True if the target .md file exists, False otherwise
        """
        source_path = getattr(page, "source_path", None)
        if not source_path:
            logger.debug(
                "link_validation_skipped",
                link=link_path,
                reason="no_source_path",
            )
            return True  # Graceful degradation

        # Get the directory containing the source file
        source_dir = Path(source_path).parent

        # Resolve the relative link against the source directory
        # Handle ./file.md, ../file.md, and plain file.md patterns
        if link_path.startswith("./"):
            target_path = source_dir / link_path[2:]
        elif link_path.startswith("../"):
            # Count parent directory traversals
            remaining = link_path
            current_dir = source_dir
            while remaining.startswith("../"):
                current_dir = current_dir.parent
                remaining = remaining[3:]
            target_path = current_dir / remaining
        else:
            # Plain filename like "sibling.md" - relative to current directory
            target_path = source_dir / link_path

        # Normalize the path
        try:
            target_path = target_path.resolve()
        except (OSError, ValueError):
            # Path resolution failed
            return False

        # Check if this target exists in our source paths
        target_str = str(target_path)
        is_valid = target_str in self._source_paths if self._source_paths else False

        # Also try checking if the file actually exists on disk
        if not is_valid and target_path.exists():
            is_valid = True

        if is_valid:
            logger.debug(
                "validating_relative_md_link",
                link=link_path,
                resolved=str(target_path),
                page=str(source_path),
                result="valid",
            )
            self.validated_urls.add(link_path)
        else:
            logger.debug(
                "validating_relative_md_link",
                link=link_path,
                resolved=str(target_path),
                page=str(source_path),
                result="broken",
            )

        return is_valid


class LinkValidatorWrapper(BaseValidator):
    """
    Health check wrapper for link validation.

    Integrates LinkValidator into the health check system and provides
    observability stats for link validation performance tracking.

    Implements HasStats protocol for observability.
    """

    name = "Links"
    description = "Validates internal and external links"
    enabled_by_default = True

    # Store stats from last validation for observability
    last_stats: ValidatorStats | None = None

    @override
    def validate(self, site: Site, build_context: Any = None) -> list[CheckResult]:
        """
        Validate links in generated pages.

        Collects stats on:
        - Total pages checked
        - Links validated
        - Cache hits/misses (from link validator)
        - Sub-timings for discovery and validation phases

        Args:
            site: Site instance to validate
            build_context: Optional BuildContext (unused in link validation)

        Returns:
            List of CheckResult objects
        """
        results = []
        sub_timings: dict[str, float] = {}

        # Initialize stats
        stats = ValidatorStats(pages_total=len(site.pages))

        # Only run if link validation is enabled
        if not site.config.get("validate_links", True):
            results.append(CheckResult.info("Link validation disabled in config"))
            stats.pages_skipped["disabled"] = len(site.pages)
            self.last_stats = stats
            return results

        # Run link validator
        t0 = time.time()
        validator = LinkValidator()
        broken_links = validator.validate_site(site)
        sub_timings["validate"] = (time.time() - t0) * 1000

        # Track stats
        stats.pages_processed = len(site.pages)

        # Track link count and broken links as metrics
        total_links = sum(len(getattr(page, "links", [])) for page in site.pages)
        stats.metrics["total_links"] = total_links
        stats.metrics["broken_links"] = len(broken_links) if broken_links else 0

        if broken_links:
            # broken_links is list of (page_path, link_url) tuples
            # Group by type based on the link URL (second element)
            internal_broken = [
                (page, link)
                for page, link in broken_links
                if not link.startswith(("http://", "https://"))
            ]
            external_broken = [
                (page, link)
                for page, link in broken_links
                if link.startswith(("http://", "https://"))
            ]

            def _relative_path(path: str) -> str:
                """Convert absolute path to project-relative path for display."""
                try:
                    return str(Path(path).relative_to(site.root_path))
                except ValueError:
                    return path  # Fallback to original if not under root

            if internal_broken:
                # Format as "page: link" for display (using relative paths)
                details = [f"{_relative_path(page)}: {link}" for page, link in internal_broken[:5]]
                results.append(
                    CheckResult.error(
                        f"{len(internal_broken)} broken internal link(s)",
                        recommendation="Fix broken internal links. They point to pages that don't exist.",
                        details=details,
                    )
                )

            if external_broken:
                details = [f"{_relative_path(page)}: {link}" for page, link in external_broken[:5]]
                results.append(
                    CheckResult.warning(
                        f"{len(external_broken)} broken external link(s)",
                        recommendation="External links may be temporarily unavailable or incorrect.",
                        details=details,
                    )
                )
        # No success message - if all links are valid, silence is golden

        # Store stats
        stats.sub_timings = sub_timings
        self.last_stats = stats

        return results


# Convenience function for direct validation
def validate_links(page: Page, site: Site | None = None) -> list[str]:
    """
    Validate all links in a page.

    Convenience function for use by rendering pipeline and other callers.

    Args:
        page: Page to validate
        site: Optional Site instance for URL resolution

    Returns:
        List of broken link URLs
    """
    validator = LinkValidator(site)
    return validator.validate_page_links(page, site)
