"""
Link validation for catching broken links.

This module provides the single source of truth for link validation in Bengal.
It validates internal links in pages against the site's page URLs to catch
broken links during build time.

Key features:
- Validates internal links resolve to existing pages or auxiliary outputs
- Handles relative paths and fragments
- Supports trailing slash variations
- Includes output_formats URLs (e.g. index.txt) when llm_txt is enabled
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
from urllib.parse import urlparse

from bengal.build.contracts.keys import content_key
from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, ValidatorStats
from bengal.health.scope import get_validation_scope
from bengal.health.utils import relative_path
from bengal.health.validators.link_skip_rules import should_skip_link
from bengal.rendering.reference_registry import (
    InternalReferenceResolver,
    build_reference_resolver,
)
from bengal.rendering.reference_resolution import (
    resolved_path_url_variants as _resolved_path_url_variants,
)
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from bengal.health.scope import ValidationScope
    from bengal.protocols import PageLike, SiteLike

logger = get_logger(__name__)


def _format_link_location(page_path: Path | None, root: Path) -> str:
    """Format a broken-link source location, including unknown sources."""
    return "<unknown>" if page_path is None else relative_path(page_path, root)


def _cached_broken_links(scope: ValidationScope | None) -> list[tuple[Path | None, str]]:
    """Extract cached broken-link metadata from scoped validation results."""
    if scope is None:
        return []

    broken_links: list[tuple[Path | None, str]] = []
    for result in scope.cached_results():
        metadata = result.metadata or {}
        source = metadata.get("source_path")
        links = metadata.get("broken_links")
        if not isinstance(source, str) or not isinstance(links, list):
            continue
        source_path = Path(source)
        broken_links.extend((source_path, link) for link in links if isinstance(link, str))
    return broken_links


def _file_results_by_source(
    broken_links: list[tuple[Path | None, str]],
    site: SiteLike,
) -> dict[Path, list[CheckResult]]:
    """Build cacheable per-source results from freshly validated broken links."""
    grouped: dict[Path, list[str]] = {}
    for source_path, link in broken_links:
        if source_path is None:
            continue
        grouped.setdefault(source_path, []).append(link)

    file_results: dict[Path, list[CheckResult]] = {}
    for source_path, links in grouped.items():
        internal_links = [link for link in links if not link.startswith(("http://", "https://"))]
        external_links = [link for link in links if link.startswith(("http://", "https://"))]
        results = []
        if internal_links:
            results.append(
                CheckResult.error(
                    f"{len(internal_links)} broken internal link(s)",
                    code="H101",
                    recommendation="Fix broken internal links. They point to pages that don't exist.",
                    details=[
                        f"{_format_link_location(source_path, site.root_path)}: {link}"
                        for link in internal_links[:5]
                    ],
                    metadata={
                        "source_path": str(source_path),
                        "broken_links": internal_links,
                    },
                )
            )
        if external_links:
            results.append(
                CheckResult.warning(
                    f"{len(external_links)} broken external link(s)",
                    code="H102",
                    recommendation="External links may be temporarily unavailable or incorrect.",
                    details=[
                        f"{_format_link_location(source_path, site.root_path)}: {link}"
                        for link in external_links[:5]
                    ],
                    metadata={
                        "source_path": str(source_path),
                        "broken_links": external_links,
                    },
                )
            )
        file_results[source_path] = results

    return file_results


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

    def __init__(self, site: SiteLike | None = None) -> None:
        """
        Initialize the link validator.

        Args:
            site: Optional Site instance for URL resolution
        """
        self.validated_urls: set[str] = set()
        self.broken_links: list[tuple[Path | None, str]] = []
        self._page_urls: set[str] | None = None
        self._source_paths: set[str] | None = None
        self._anchors_by_url: dict[str, frozenset[str]] | None = None
        self._resolver: InternalReferenceResolver | None = None
        self._site: SiteLike | None = site
        self._link_result_cache: dict[tuple[str, str, str], bool] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def _llm_txt_enabled(self, site: Any) -> bool:
        """Check if output_formats.llm_txt is enabled (index.txt generated per page)."""
        of = getattr(site, "config", {}) or {}
        of = of.get("output_formats", {}) or {}
        if not of.get("enabled", True):
            return False
        per_page = of.get("per_page", [])
        return "llm_txt" in per_page

    def _build_auxiliary_url_index(self, site: Any) -> set[str]:
        """
        Build index of auxiliary output URLs (e.g. index.txt) when enabled.

        The action bar links to index.txt for LLM/AI discovery. These are valid
        when output_formats.per_page includes "llm_txt". Uses same URL convention
        as action-bar.html: page_url + "index.txt".

        Args:
            site: Site instance with pages and config

        Returns:
            Set of valid auxiliary URLs
        """
        if not self._llm_txt_enabled(site):
            return set()
        urls: set[str] = set()
        for page in site.pages:
            url = getattr(page, "href", None)
            if url:
                base = url.rstrip("/") + "/"
                urls.add(base + "index.txt")
        return urls

    def _build_page_url_index(self, site: Any) -> set[str]:
        """
        Build an index of all valid internal link targets for fast lookup.

        Includes page URLs and auxiliary outputs (index.txt) when output_formats
        are enabled. Creates normalized URL variants (with/without trailing
        slashes) for flexible matching.

        Args:
            site: Site instance containing pages

        Returns:
            Set of all valid internal link targets
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

        urls.update(self._build_auxiliary_url_index(site))
        return urls

    def _build_source_path_index(self, site: Any) -> set[str]:
        """
        Build an index of all source paths for resolving relative links.

        Used to validate relative links like ./sibling.md against actual source files.
        Uses content_key for consistent path format (discovery vs resolved target).

        Args:
            site: Site instance containing pages

        Returns:
            Set of content keys (normalized, relative to site root)
        """
        paths: set[str] = set()
        root = site.root_path

        for page in site.pages:
            source_path = getattr(page, "source_path", None)
            if source_path:
                full = (
                    (root / source_path)
                    if not Path(source_path).is_absolute()
                    else Path(source_path)
                )
                paths.add(content_key(full, root))

        return paths

    def validate_page_links(self, page: PageLike, site: Any | None = None) -> list[str]:
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

        # Build indexes on first use or when reusing this validator with a different site.
        if site is not None and (self._page_urls is None or site is not self._site):
            self._load_reference_registry(site)
            self._site = site
            self._reset_result_cache()

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

    def validate_site(
        self, site: Any, pages: list[PageLike] | None = None
    ) -> list[tuple[Path | None, str]]:
        """
        Validate all links in the entire site.

        Args:
            site: Site instance

        Returns:
            List of (page_path, broken_link) tuples
        """
        pages_to_validate = list(site.pages) if pages is None else pages
        logger.debug(
            "validating_site_links",
            page_count=len(pages_to_validate),
            total_pages=len(site.pages),
        )

        # Reset state
        self.broken_links = []
        self.validated_urls = set()
        self._reset_result_cache()
        self._site = site
        self._load_reference_registry(site)

        for page in pages_to_validate:
            self.validate_page_links(page, site)

        if self.broken_links:
            pages_affected = len({str(page_path) for page_path, _ in self.broken_links})

            logger.warning(
                "found_broken_links",
                total_broken=len(self.broken_links),
                pages_affected=pages_affected,
                sample_links=[
                    (_format_link_location(p, site.root_path), link)
                    for p, link in self.broken_links[:10]
                ],
            )
        else:
            logger.debug(
                "link_validation_complete",
                total_links_checked=len(self.validated_urls),
                broken_links=0,
            )

        return self.broken_links

    def _is_valid_link(self, link: str, page: PageLike) -> bool:
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
        if should_skip_link(link):
            self.validated_urls.add(link)
            return True

        # Parse the link
        parsed = urlparse(link)

        # Fragment-only links (e.g., "#section") — validate anchor exists on current page
        if not parsed.path and parsed.fragment:
            page_key = str(
                getattr(page, "_path", None)
                or getattr(page, "href", None)
                or getattr(page, "source_path", "")
            )
            return self._cached_link_result(
                ("fragment", page_key, link),
                link,
                lambda: self._validate_fragment_link(link, parsed.fragment, page),
            )

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
            source_key = str(getattr(page, "source_path", ""))
            return self._cached_link_result(
                ("source", source_key, link),
                parsed.path,
                lambda: self._validate_relative_md_link(parsed.path, page),
            )

        # Get page's URL for resolving other relative links
        page_url = getattr(page, "href", None)
        if not page_url:
            logger.debug(
                "link_validation_skipped",
                link=link,
                reason="no_page_url",
            )
            return True

        page_url = str(page_url)
        return self._cached_link_result(
            ("url", page_url, link),
            link,
            lambda: self._validate_internal_link(
                link, parsed.path, parsed.fragment, page, page_url
            ),
        )

    def _cached_link_result(
        self,
        cache_key: tuple[str, str, str],
        valid_marker: str,
        compute: Callable[[], bool],
    ) -> bool:
        """Return a cached per-run link result, preserving valid-link accounting."""
        cached = self._link_result_cache.get(cache_key)
        if cached is not None:
            self.cache_hits += 1
            if cached:
                self.validated_urls.add(valid_marker)
            return cached

        self.cache_misses += 1
        result = compute()
        self._link_result_cache[cache_key] = result
        return result

    def _reset_result_cache(self) -> None:
        """Clear per-run link result memoization and counters."""
        self._link_result_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def _validate_fragment_link(self, link: str, fragment: str, page: PageLike) -> bool:
        """Validate a fragment-only link against the current page's anchors."""
        if self._anchors_by_url is not None:
            page_path = getattr(page, "_path", None)
            if page_path:
                anchors = (
                    self._resolver.anchors_for(page_path)
                    if self._resolver is not None
                    else self._anchors_by_url.get(page_path, frozenset())
                )
                if anchors and fragment not in anchors:
                    logger.debug(
                        "validating_fragment_link",
                        link=link,
                        page=str(page.source_path),
                        result="broken_anchor",
                        fragment=fragment,
                    )
                    return False
        logger.debug(
            "validating_fragment_link",
            link=link,
            page=str(page.source_path),
            result="valid",
        )
        self.validated_urls.add(link)
        return True

    def _validate_internal_link(
        self,
        link: str,
        link_path: str,
        fragment: str,
        page: PageLike,
        page_url: str,
    ) -> bool:
        """Validate an internal page URL plus optional anchor."""
        if self._resolver is not None:
            resolved_path = self._resolver.resolve(page_url, str(link_path))
            is_valid = self._resolver.has_url(resolved_path)
        else:
            from bengal.rendering.reference_resolution import (
                resolve_internal_link,
                resolved_path_url_variants,
            )

            resolved_path = resolve_internal_link(page_url, str(link_path))
            variants = resolved_path_url_variants(resolved_path)
            page_urls = self._page_urls
            is_valid = page_urls is not None and any(v in page_urls for v in variants)

        if is_valid:
            # If link has a fragment, also validate the anchor exists
            if fragment and self._anchors_by_url is not None:
                anchors = (
                    self._resolver.anchors_for(resolved_path)
                    if self._resolver is not None
                    else self._anchors_by_url.get(resolved_path, frozenset())
                )
                if not anchors and self._anchors_by_url is not None:
                    anchors = self._anchors_by_url.get(
                        resolved_path.rstrip("/"), frozenset()
                    ) or self._anchors_by_url.get(resolved_path.rstrip("/") + "/", frozenset())
                if anchors and fragment not in anchors:
                    logger.debug(
                        "validating_internal_link",
                        link=link,
                        resolved=resolved_path,
                        page=str(page.source_path),
                        result="broken_anchor",
                        fragment=fragment,
                    )
                    return False

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
                checked_variants=list(_resolved_path_url_variants(resolved_path))[:3],
            )

        return is_valid

    def _load_reference_registry(self, site: Any) -> None:
        """Load rendering-owned registry data for validation."""
        self._resolver = build_reference_resolver(site)
        registry = self._resolver.registry
        self._page_urls = set(self._resolver.all_urls)
        self._source_paths = set(registry.source_paths)
        self._anchors_by_url = dict(registry.anchors_by_url)

    def _validate_relative_md_link(self, link_path: str, page: PageLike) -> bool:
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
        except OSError, ValueError:
            # Path resolution failed
            return False

        # Check if this target exists in our source paths (content_key for alignment)
        site = getattr(self, "_site", None)
        if site and self._source_paths:
            target_key = content_key(target_path, site.root_path)
            is_valid = target_key in self._source_paths
        else:
            is_valid = False

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
    consumes_validation_scope_cache = True

    # Store stats from last validation for observability
    last_stats: ValidatorStats | None = None
    last_file_results: dict[Path, list[CheckResult]] | None = None

    @override
    def validate(self, site: SiteLike, build_context: Any = None) -> list[CheckResult]:
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
        self.last_file_results = None

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
        scope = get_validation_scope(build_context)
        pages_to_validate = scope.pages_to_validate(site) if scope is not None else list(site.pages)
        broken_links = validator.validate_site(site, pages=pages_to_validate)
        sub_timings["validate"] = (time.time() - t0) * 1000
        cached_broken_links = _cached_broken_links(scope)
        all_broken_links = cached_broken_links + broken_links

        # Track stats
        stats.pages_processed = len(pages_to_validate)
        if scope is not None:
            skipped = len(site.pages) - len(pages_to_validate) - scope.cached_file_count
            if skipped > 0:
                stats.pages_skipped["unscoped"] = skipped

        # Track link count and broken links as metrics
        total_links = sum(len(getattr(page, "links", [])) for page in pages_to_validate)
        stats.cache_hits = validator.cache_hits
        stats.cache_misses = validator.cache_misses
        stats.metrics["total_links"] = total_links
        stats.metrics["unique_link_checks"] = validator.cache_misses
        stats.metrics["broken_links"] = len(all_broken_links) if all_broken_links else 0
        if scope is not None:
            stats.metrics["cached_files"] = scope.cached_file_count
            stats.metrics["cached_results"] = scope.cached_result_count
            stats.metrics["scoped_pages"] = len(pages_to_validate)
            stats.metrics["site_links"] = sum(
                len(getattr(page, "links", [])) for page in site.pages
            )

        self.last_file_results = _file_results_by_source(broken_links, site)

        if all_broken_links:
            # broken_links is list of (page_path, link_url) tuples
            # Group by type based on the link URL (second element)
            internal_broken = [
                (page, link)
                for page, link in all_broken_links
                if not link.startswith(("http://", "https://"))
            ]
            external_broken = [
                (page, link)
                for page, link in all_broken_links
                if link.startswith(("http://", "https://"))
            ]

            if internal_broken:
                # Format as "page: link" for display (using relative paths)
                details = [
                    f"{_format_link_location(page, site.root_path)}: {link}"
                    for page, link in internal_broken[:5]
                ]
                results.append(
                    CheckResult.error(
                        f"{len(internal_broken)} broken internal link(s)",
                        code="H101",
                        recommendation="Fix broken internal links. They point to pages that don't exist.",
                        details=details,
                    )
                )

            if external_broken:
                details = [
                    f"{_format_link_location(page, site.root_path)}: {link}"
                    for page, link in external_broken[:5]
                ]
                results.append(
                    CheckResult.warning(
                        f"{len(external_broken)} broken external link(s)",
                        code="H102",
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
def validate_links(page: PageLike, site: SiteLike | None = None) -> list[str]:
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
