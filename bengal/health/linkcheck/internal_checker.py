"""
Internal link checker for page-to-page and anchor validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from bengal.health.linkcheck.ignore_policy import IgnorePolicy
from bengal.health.linkcheck.models import LinkCheckResult, LinkKind, LinkStatus
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


class InternalLinkChecker:
    """
    Checker for internal links within a site.

    Validates:
    - Page-to-page links (resolved via paths)
    - Anchor links to headings (#section-id)
    - Relative links and absolute site links
    """

    def __init__(
        self,
        site: Site,
        ignore_policy: IgnorePolicy | None = None,
    ):
        """
        Initialize internal link checker.

        Args:
            site: Site instance with pages and xref_index
            ignore_policy: Policy for ignoring certain links
        """
        self.site = site
        self.ignore_policy = ignore_policy or IgnorePolicy()

        # Build index of output paths for fast lookup
        self._output_paths: set[str] = set()
        self._anchors_by_page: dict[str, set[str]] = {}

        for page in site.pages:
            if page.output_path:
                # Normalize to URL format
                url = page.url if hasattr(page, "url") else f"/{page.slug}/"
                self._output_paths.add(url.rstrip("/"))
                self._output_paths.add(url)  # Also with trailing slash

                # Extract anchors from page TOC or metadata
                if hasattr(page, "toc") and page.toc:
                    anchors = set()
                    for item in page.toc:
                        if "id" in item:
                            anchors.add(item["id"])
                    self._anchors_by_page[url] = anchors

    def check_links(self, links: list[tuple[str, str]]) -> dict[str, LinkCheckResult]:
        """
        Check internal links.

        Args:
            links: List of (url, first_ref) tuples

        Returns:
            Dict mapping URL to LinkCheckResult
        """
        # Group URLs by destination and count references
        url_refs: dict[str, list[str]] = {}
        for url, ref in links:
            if url not in url_refs:
                url_refs[url] = []
            url_refs[url].append(ref)

        # Check each URL
        results: dict[str, LinkCheckResult] = {}
        for url, refs in url_refs.items():
            results[url] = self._check_internal_link(url, refs)

        return results

    def _check_internal_link(self, url: str, refs: list[str]) -> LinkCheckResult:
        """
        Check a single internal link.

        Args:
            url: Internal URL to check
            refs: List of pages that reference this URL

        Returns:
            LinkCheckResult
        """
        # Check ignore policy
        should_ignore, ignore_reason = self.ignore_policy.should_ignore_url(url)
        if should_ignore:
            logger.debug("ignoring_internal_url", url=url, reason=ignore_reason)
            return LinkCheckResult(
                url=url,
                kind=LinkKind.INTERNAL,
                status=LinkStatus.IGNORED,
                first_ref=refs[0] if refs else None,
                ref_count=len(refs),
                ignored=True,
                ignore_reason=ignore_reason,
            )

        # Parse URL to separate path and fragment
        parsed = urlparse(url)
        path = parsed.path
        fragment = parsed.fragment

        # Handle relative paths (resolve to absolute)
        if not path.startswith("/"):
            # For now, treat relative as potentially valid
            # A full implementation would resolve relative to the referencing page
            logger.debug(
                "skipping_relative_internal_link",
                url=url,
                reason="relative paths not yet fully supported",
            )
            return LinkCheckResult(
                url=url,
                kind=LinkKind.INTERNAL,
                status=LinkStatus.OK,
                first_ref=refs[0] if refs else None,
                ref_count=len(refs),
                metadata={"note": "relative path - validation skipped"},
            )

        # Check if page exists
        path_normalized = path.rstrip("/")
        page_exists = path_normalized in self._output_paths or path in self._output_paths

        if not page_exists:
            logger.debug("internal_link_broken_page_not_found", url=url, path=path)
            return LinkCheckResult(
                url=url,
                kind=LinkKind.INTERNAL,
                status=LinkStatus.BROKEN,
                reason="Page not found",
                first_ref=refs[0] if refs else None,
                ref_count=len(refs),
            )

        # If fragment specified, check if anchor exists
        if fragment:
            # Find the page
            page_url = path if path in self._output_paths else path_normalized
            anchors = self._anchors_by_page.get(page_url, set())

            if anchors and fragment not in anchors:
                logger.debug(
                    "internal_link_broken_anchor_not_found",
                    url=url,
                    page=page_url,
                    anchor=fragment,
                    available_anchors=list(anchors)[:5],
                )
                return LinkCheckResult(
                    url=url,
                    kind=LinkKind.INTERNAL,
                    status=LinkStatus.BROKEN,
                    reason=f"Anchor #{fragment} not found in page",
                    first_ref=refs[0] if refs else None,
                    ref_count=len(refs),
                    metadata={"available_anchors": list(anchors)[:10]},
                )

        # Link is valid
        logger.debug("internal_link_ok", url=url)
        return LinkCheckResult(
            url=url,
            kind=LinkKind.INTERNAL,
            status=LinkStatus.OK,
            first_ref=refs[0] if refs else None,
            ref_count=len(refs),
        )
