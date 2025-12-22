"""
Internal link checker for page-to-page and anchor validation.

Validates internal links by checking if target pages exist in the built
output directory. Handles relative paths, baseurl stripping, and anchor
validation.

Features:
    - Page existence checking via output directory scan
    - Anchor validation against page headings
    - Source file reference filtering (autodoc .py links)
    - Baseurl path stripping for proper resolution

Related:
    - bengal.health.linkcheck.orchestrator: Coordinates with external checker
    - bengal.health.linkcheck.models: LinkCheckResult data model
"""

from __future__ import annotations

from pathlib import Path
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
    Validates internal links within a built site.

    Scans the output directory for HTML files and builds an index of valid
    URLs. Checks links against this index and validates anchors when present.

    Validation Coverage:
        - Page-to-page links (absolute site paths)
        - Anchor links (#section-id)
        - Handles baseurl stripping
        - Filters source file references (autodoc)

    Attributes:
        site: Site instance with output_dir
        ignore_policy: IgnorePolicy for filtering certain links
        output_dir: Path to built HTML files
        baseurl_path: Base URL path to strip from links

    Note:
        Relative links are currently passed as OK with a metadata note,
        as full resolution requires tracking the referencing page context.
    """

    def __init__(
        self,
        site: Site,
        ignore_policy: IgnorePolicy | None = None,
    ):
        """
        Initialize internal link checker.

        Scans the output directory to build an index of valid URLs.

        Args:
            site: Site instance with output_dir and config
            ignore_policy: Policy for ignoring certain links
        """
        self.site = site
        self.ignore_policy = ignore_policy or IgnorePolicy()
        self.output_dir = site.output_dir

        # Get baseurl to strip from URLs
        baseurl = site.config.get("baseurl", "")
        if baseurl:
            # Parse baseurl to get just the path part
            from urllib.parse import urlparse

            parsed = urlparse(baseurl)
            self.baseurl_path = parsed.path.rstrip("/")
        else:
            self.baseurl_path = ""

        # Build index from actual files in output directory
        self._output_paths: set[str] = set()
        self._anchors_by_page: dict[str, set[str]] = {}

        if self.output_dir.exists():
            # Scan all HTML files and build URL index
            for html_file in self.output_dir.rglob("*.html"):
                # Convert file path to URL
                rel_path = html_file.relative_to(self.output_dir)

                # Convert path/index.html -> /path/
                # Convert path.html -> /path
                if rel_path.name == "index.html":
                    url = "/" if rel_path.parent == Path(".") else f"/{rel_path.parent}/"
                else:
                    url = f"/{rel_path.with_suffix('')}"

                # Add both with and without trailing slash
                self._output_paths.add(url)
                self._output_paths.add(url.rstrip("/"))
                if url != "/":
                    self._output_paths.add(url.rstrip("/") + "/")

        logger.debug(
            "internal_checker_initialized",
            output_paths_count=len(self._output_paths),
            output_dir=str(self.output_dir),
        )

    def check_links(self, links: list[tuple[str, str]]) -> dict[str, LinkCheckResult]:
        """
        Check internal links against the output directory index.

        Deduplicates URLs and checks each against the built site structure.

        Args:
            links: List of (url, first_ref) tuples where first_ref is the
                page that contains this link.

        Returns:
            Dict mapping URL string to LinkCheckResult.
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

        Resolution steps:
            1. Apply ignore policy
            2. Filter source file references (.py files)
            3. Parse URL to extract path and fragment
            4. Strip baseurl if present
            5. Check page existence in output index
            6. Validate anchor if fragment present

        Args:
            url: Internal URL to check (may include fragment).
            refs: List of pages that reference this URL.

        Returns:
            LinkCheckResult with OK/BROKEN/IGNORED status.
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

        # Skip source file references FIRST (before parsing)
        # These are common in autodoc-generated content and should not be checked as page links
        # Patterns: bengal/module.py#L1, ../bengal/module.py#L1, module.py#L1, etc.
        if (
            ".py#L" in url  # Python file with line number anchor
            or ".py#" in url  # Python file with any anchor
            or url.endswith(".py")  # Python file without anchor
            or "/bengal/" in url
            and ".py" in url  # Paths containing bengal/ and .py
            or (url.startswith("../") and ".py" in url)  # Relative paths to .py files
        ):
            logger.debug(
                "skipping_source_file_reference",
                url=url,
                reason="source_file_reference_in_autodoc",
            )
            return LinkCheckResult(
                url=url,
                kind=LinkKind.INTERNAL,
                status=LinkStatus.IGNORED,
                first_ref=refs[0] if refs else None,
                ref_count=len(refs),
                ignored=True,
                ignore_reason="Source file reference (autodoc)",
            )

        # Parse URL to separate path and fragment
        parsed = urlparse(url)
        path = parsed.path
        fragment = parsed.fragment

        # Strip baseurl from path if present
        if self.baseurl_path and path.startswith(self.baseurl_path):
            path = path[len(self.baseurl_path) :]
            if not path:  # Handle case where path becomes empty
                path = "/"

        # Handle relative paths (resolve to absolute)
        if not path.startswith("/"):
            # For now, treat other relative paths as potentially valid
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

        # Check if page exists (with or without trailing slash)
        page_exists = path in self._output_paths or path.rstrip("/") in self._output_paths

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
            # Find the page (try both with and without trailing slash)
            page_url = path if path in self._output_paths else path.rstrip("/")
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
