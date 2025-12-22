"""
Link check orchestrator coordinating internal and external validation.

The orchestrator extracts links from built HTML files, classifies them as
internal or external, and delegates to specialized checkers. Results are
consolidated into reports for console output and JSON serialization.

Architecture:
    1. Extract links from output_dir/*.html using HTML parsing
    2. Classify links (http/https -> external, else -> internal)
    3. Run InternalLinkChecker and AsyncLinkChecker concurrently
    4. Build consolidated results and summary

Related:
    - bengal.health.linkcheck.async_checker: External link checking
    - bengal.health.linkcheck.internal_checker: Internal link checking
    - bengal.health.validators.links: LinkValidator health check
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
    Orchestrates internal and external link checking.

    Extracts links from built HTML files, classifies them, and delegates to
    specialized checkers. Provides consolidated results and multiple output
    formats (console, JSON).

    Features:
        - HTML parsing to extract href attributes
        - Automatic internal/external classification
        - Concurrent checking with ignore policies
        - Console and JSON report formatting

    Attributes:
        site: Site instance with output_dir
        check_internal: Whether to validate internal links
        check_external: Whether to validate external links
        config: Configuration dict for checkers and ignore policy
        ignore_policy: IgnorePolicy instance for filtering
        internal_checker: InternalLinkChecker (if check_internal)
        external_checker: AsyncLinkChecker (if check_external)

    Example:
        >>> orchestrator = LinkCheckOrchestrator(site, check_external=True)
        >>> results, summary = orchestrator.check_all_links()
        >>> if not summary.passed:
        ...     print(orchestrator.format_console_report(results, summary))
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
            site: Site instance with built output directory
            check_internal: Whether to check internal page/anchor links
            check_external: Whether to check external HTTP links
            config: Configuration dict with optional keys:
                - exclude: URL patterns to ignore
                - exclude_domain: Domains to ignore
                - ignore_status: Status codes to ignore
                - max_concurrency: Concurrent request limit
                - timeout: Request timeout in seconds
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
        Check all links in the built site.

        Extracts links from HTML files, checks internal and external links
        according to configuration, and returns consolidated results.

        Returns:
            Tuple of (results, summary) where results is a list of
            LinkCheckResult and summary is LinkCheckSummary.
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
        Extract all links from built HTML files.

        Parses HTML files in output_dir, extracts href attributes from anchor
        tags (excluding those inside code blocks), and classifies as internal
        or external based on URL scheme.

        Returns:
            Tuple of (internal_links, external_links) where each is a list of
            (url, page_path) tuples. page_path is the relative path of the
            HTML file that contains the link.

        Note:
            Skips mailto:, tel:, data:, and javascript: URLs.
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
            """
            HTML parser that extracts href links, skipping code blocks.

            Tracks nesting depth in <code> and <pre> tags to avoid extracting
            code examples as real links.
            """

            def __init__(self) -> None:
                super().__init__()
                self.links: list[str] = []
                self._in_code_block = 0  # Track nesting depth of code blocks

            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                # Track code block tags
                if tag in ("code", "pre"):
                    self._in_code_block += 1
                # Only extract links if not inside a code block
                elif tag == "a" and self._in_code_block == 0:
                    for attr, value in attrs:
                        if attr == "href" and value:
                            self.links.append(value)

            def handle_endtag(self, tag: str) -> None:
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
        Build aggregate summary from individual results.

        Args:
            results: List of LinkCheckResult objects.
            duration_ms: Total check duration in milliseconds.

        Returns:
            LinkCheckSummary with counts by status and total duration.
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
        Format results as JSON-serializable report.

        Suitable for CI integration, API responses, or file output.

        Args:
            results: List of LinkCheckResult objects.
            summary: LinkCheckSummary with aggregate statistics.

        Returns:
            Dict with status ("passed"/"failed"), summary, and results array.
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
        Format results as human-readable console report.

        Includes summary statistics, broken link details (first 20), and
        error details (first 10) with emoji status indicators.

        Args:
            results: List of LinkCheckResult objects.
            summary: LinkCheckSummary with aggregate statistics.

        Returns:
            Multi-line string formatted for terminal output.
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
