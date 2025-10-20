"""
Link validation for catching broken links.
"""


from __future__ import annotations

from typing import Any

from bengal.core.page import Page
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class LinkValidator:
    """
    Validates links in pages to catch broken links.
    """

    def __init__(self) -> None:
        """Initialize the link validator."""
        self.validated_urls: set = set()
        self.broken_links: list[tuple] = []

    def validate_page_links(self, page: Page) -> list[str]:
        """
        Validate all links in a page.

        Args:
            page: Page to validate

        Returns:
            List of broken link URLs
        """
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

        self.broken_links = []

        for page in site.pages:
            self.validate_page_links(page)

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

        Args:
            link: Link URL to check
            page: Page containing the link

        Returns:
            True if link is valid, False otherwise
        """
        # Skip external links (http/https)
        if link.startswith(("http://", "https://", "mailto:", "tel:", "#")):
            logger.debug(
                "skipping_external_link",
                link=link[:100],
                type="external" if link.startswith("http") else "special",
            )
            return True

        # Skip data URLs
        if link.startswith("data:"):
            return True

        # Check if it's a relative link to another page
        # This is a simplified check - a full implementation would
        # resolve the link and check if the target exists

        # For now, assume internal links are valid
        # A full implementation would need to:
        # 1. Resolve the link relative to the page
        # 2. Check if the target file exists in the output
        # 3. Handle anchors (#sections)

        logger.debug(
            "validating_internal_link", link=link, page=str(page.source_path), result="valid"
        )

        return True
