"""
Link check orchestrator - coordinates internal and external checking.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from bengal.health.linkcheck.async_checker import AsyncLinkChecker
from bengal.health.linkcheck.ignore_policy import IgnorePolicy
from bengal.health.linkcheck.internal_checker import InternalLinkChecker
from bengal.health.linkcheck.models import (
    LinkCheckResult,
    LinkCheckSummary,
    LinkStatus,
)
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


class LinkCheckOrchestrator:
    """
    Orchestrates link checking across internal and external links.

    Features:
    - Extracts links from all pages
    - Separates internal vs external
    - Checks both concurrently
    - Applies ignore policies
    - Returns consolidated results
    """

    def __init__(
        self,
        site: Site,
        check_internal: bool = True,
        check_external: bool = True,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize link check orchestrator.

        Args:
            site: Site instance
            check_internal: Whether to check internal links
            check_external: Whether to check external links
            config: Configuration dict for checkers
        """
        self.site = site
        self.check_internal = check_internal
        self.check_external = check_external
        self.config = config or {}

        # Create ignore policy
        self.ignore_policy = IgnorePolicy.from_config(self.config)

        # Create checkers
        if self.check_internal:
            self.internal_checker = InternalLinkChecker(site, self.ignore_policy)
        if self.check_external:
            self.external_checker = AsyncLinkChecker.from_config(self.config)

    def check_all_links(self) -> tuple[list[LinkCheckResult], LinkCheckSummary]:
        """
        Check all links in the site.

        Returns:
            Tuple of (results list, summary)
        """
        start_time = time.time()

        # Extract all links from pages
        internal_links, external_links = self._extract_links()

        logger.info(
            "link_check_starting",
            internal_count=len(internal_links),
            external_count=len(external_links),
            check_internal=self.check_internal,
            check_external=self.check_external,
        )

        # Check internal and external links
        results: list[LinkCheckResult] = []

        if self.check_internal and internal_links:
            internal_results = self.internal_checker.check_links(internal_links)
            results.extend(internal_results.values())
            logger.info(
                "internal_links_checked",
                count=len(internal_results),
                broken=sum(1 for r in internal_results.values() if r.status == LinkStatus.BROKEN),
            )

        if self.check_external and external_links:
            # Run async checker
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                external_results = loop.run_until_complete(
                    self.external_checker.check_links(external_links)
                )
                results.extend(external_results.values())
                logger.info(
                    "external_links_checked",
                    count=len(external_results),
                    broken=sum(
                        1 for r in external_results.values() if r.status == LinkStatus.BROKEN
                    ),
                )
            finally:
                loop.close()

        # Build summary
        duration_ms = (time.time() - start_time) * 1000
        summary = self._build_summary(results, duration_ms)

        logger.info(
            "link_check_complete",
            total=summary.total_checked,
            ok=summary.ok_count,
            broken=summary.broken_count,
            ignored=summary.ignored_count,
            errors=summary.error_count,
            duration_ms=round(duration_ms, 2),
        )

        return results, summary

    def _extract_links(self) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """
        Extract all links from built HTML files, separated by internal vs external.

        Returns:
            Tuple of (internal_links, external_links) where each is a list of
            (url, page_path) tuples
        """
        from html.parser import HTMLParser

        internal_links: list[tuple[str, str]] = []
        external_links: list[tuple[str, str]] = []

        # Get output directory
        output_dir = self.site.output_dir
        if not output_dir.exists():
            logger.warning(
                "output_dir_not_found",
                path=str(output_dir),
                suggestion="build the site first with 'bengal site build'",
            )
            return internal_links, external_links

        class LinkExtractor(HTMLParser):
            """Extract links from HTML, skipping links inside code blocks."""

            def __init__(self):
                super().__init__()
                self.links: list[str] = []
                self._in_code_block = 0  # Track nesting depth of code blocks

            def handle_starttag(self, tag, attrs):
                # Track code block tags
                if tag in ("code", "pre"):
                    self._in_code_block += 1
                # Only extract links if not inside a code block
                elif tag == "a" and self._in_code_block == 0:
                    for attr, value in attrs:
                        if attr == "href" and value:
                            self.links.append(value)

            def handle_endtag(self, tag):
                # Exit code block when closing tag found
                if tag in ("code", "pre"):
                    self._in_code_block = max(0, self._in_code_block - 1)

        # Scan all HTML files
        for html_file in output_dir.rglob("*.html"):
            try:
                html_content = html_file.read_text(encoding="utf-8")
                parser = LinkExtractor()
                parser.feed(html_content)

                # Get relative path for reference
                rel_path = html_file.relative_to(output_dir)
                page_ref = str(rel_path)

                for link in parser.links:
                    # Skip mailto, tel, data URIs
                    if link.startswith(("mailto:", "tel:", "data:", "javascript:")):
                        continue

                    # Skip empty anchors
                    if link == "#" or not link:
                        continue

                    # Classify as internal or external
                    if link.startswith(("http://", "https://")):
                        external_links.append((link, page_ref))
                    else:
                        internal_links.append((link, page_ref))

            except Exception as e:
                logger.warning(
                    "failed_to_parse_html",
                    file=str(html_file),
                    error=str(e),
                )
                continue

        return internal_links, external_links

    def _build_summary(
        self, results: list[LinkCheckResult], duration_ms: float
    ) -> LinkCheckSummary:
        """
        Build summary from results.

        Args:
            results: List of check results
            duration_ms: Total duration in milliseconds

        Returns:
            LinkCheckSummary
        """
        summary = LinkCheckSummary(
            total_checked=len(results),
            duration_ms=duration_ms,
        )

        for result in results:
            if result.status == LinkStatus.OK:
                summary.ok_count += 1
            elif result.status == LinkStatus.BROKEN:
                summary.broken_count += 1
            elif result.status == LinkStatus.IGNORED:
                summary.ignored_count += 1
            elif result.status == LinkStatus.ERROR:
                summary.error_count += 1

        return summary

    def format_json_report(
        self, results: list[LinkCheckResult], summary: LinkCheckSummary
    ) -> dict[str, Any]:
        """
        Format results as JSON report.

        Args:
            results: List of check results
            summary: Summary statistics

        Returns:
            JSON-serializable dict
        """
        return {
            "status": "passed" if summary.passed else "failed",
            "summary": summary.to_dict(),
            "results": [r.to_dict() for r in results],
        }

    def format_console_report(
        self, results: list[LinkCheckResult], summary: LinkCheckSummary
    ) -> str:
        """
        Format results as console report.

        Args:
            results: List of check results
            summary: Summary statistics

        Returns:
            Formatted string for console output
        """
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("🔗 Link Check Report")
        lines.append("=" * 70)
        lines.append("")

        # Summary
        lines.append(f"Total checked:   {summary.total_checked}")
        lines.append(f"✅ OK:           {summary.ok_count}")
        lines.append(f"❌ Broken:       {summary.broken_count}")
        lines.append(f"⚠️  Errors:       {summary.error_count}")
        lines.append(f"⊘  Ignored:      {summary.ignored_count}")
        lines.append(f"⏱️  Duration:     {summary.duration_ms:.2f}ms")
        lines.append("")

        # Broken links
        broken = [r for r in results if r.status == LinkStatus.BROKEN]
        if broken:
            lines.append(f"❌ Broken Links ({len(broken)}):")
            lines.append("-" * 70)
            for result in broken[:20]:  # Show first 20
                lines.append(f"  {result.url}")
                if result.first_ref:
                    lines.append(f"    Referenced in: {result.first_ref}")
                if result.reason:
                    lines.append(f"    Reason: {result.reason}")
                lines.append("")

            if len(broken) > 20:
                lines.append(f"  ... and {len(broken) - 20} more")
            lines.append("")

        # Errors
        errors = [r for r in results if r.status == LinkStatus.ERROR]
        if errors:
            lines.append(f"⚠️  Errors ({len(errors)}):")
            lines.append("-" * 70)
            for result in errors[:10]:  # Show first 10
                lines.append(f"  {result.url}")
                if result.error_message:
                    lines.append(f"    Error: {result.error_message}")
                lines.append("")

            if len(errors) > 10:
                lines.append(f"  ... and {len(errors) - 10} more")
            lines.append("")

        # Final status
        lines.append("=" * 70)
        if summary.passed:
            lines.append("✅ PASSED - All links are valid")
        else:
            lines.append("❌ FAILED - Broken or error links found")
        lines.append("=" * 70)

        return "\n".join(lines)
