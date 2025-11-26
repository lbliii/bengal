"""
Link validation for catching broken links.

This module validates internal links in pages against the site's page URLs
to catch broken links during build time.

Key features:
- Validates internal links resolve to existing pages
- Handles relative paths and fragments
- Supports trailing slash variations
- Caches validation results for performance
"""


from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlparse

from bengal.core.page import Page
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


class LinkValidator:
    """
    Validates links in pages to catch broken links.

    This validator checks that internal links resolve to existing pages
    in the site. External links (http/https), mailto, tel, and fragment-only
    links are skipped (external link checking is handled by health/validators/links.py).

    Attributes:
        validated_urls: Set of URLs that have been validated (cache)
        broken_links: List of (page_path, broken_link) tuples
        _page_urls: Cached set of all page URLs for O(1) lookup
        _site: Reference to site being validated
    """

    def __init__(self, site: Site | None = None) -> None:
        """
        Initialize the link validator.

        Args:
            site: Optional Site instance for URL resolution
        """
        self.validated_urls: set[str] = set()
        self.broken_links: list[tuple] = []
        self._page_urls: set[str] | None = None
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
            url = getattr(page, "url", None)
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

        # Build URL index on first use (or if site changed)
        if self._page_urls is None and site is not None:
            self._page_urls = self._build_page_url_index(site)
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

    def validate_site(self, site: Any) -> list[tuple]:
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

        for page in site.pages:
            self.validate_page_links(page, site)

        if self.broken_links:
            pages_affected = len(set(str(page_path) for page_path, _ in self.broken_links))
            logger.warning(
                "found_broken_links",
                total_broken=len(self.broken_links),
                pages_affected=pages_affected,
                sample_links=[(str(p), link) for p, link in self.broken_links[:10]],
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

        # Get page's URL for resolving relative links
        page_url = getattr(page, "url", None)
        if not page_url:
            # Can't resolve without page URL
            logger.debug(
                "link_validation_skipped",
                link=link,
                reason="no_page_url",
            )
            return True

        # Resolve relative link against page URL
        # Ensure page_url has trailing slash for proper resolution
        base_url = page_url if page_url.endswith("/") else page_url + "/"
        resolved = urljoin(base_url, parsed.path)

        # Strip fragment for URL matching
        resolved_path = resolved.split("#")[0] if "#" in resolved else resolved

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
