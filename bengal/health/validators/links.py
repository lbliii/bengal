"""
Link validator wrapper.

Integrates the existing LinkValidator into the health check system.

Provides observability stats for link validation performance tracking.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, ValidatorStats

if TYPE_CHECKING:
    from bengal.core.site import Site


class LinkValidatorWrapper(BaseValidator):
    """
    Wrapper for link validation.

    Note: Link validation runs during post-processing. This validator
    re-runs validation or reports on previous validation results.

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
        from bengal.rendering.link_validator import LinkValidator

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
                details = [
                    f"{_relative_path(page)}: {link}"
                    for page, link in internal_broken[:5]
                ]
                results.append(
                    CheckResult.error(
                        f"{len(internal_broken)} broken internal link(s)",
                        recommendation="Fix broken internal links. They point to pages that don't exist.",
                        details=details,
                    )
                )

            if external_broken:
                details = [
                    f"{_relative_path(page)}: {link}"
                    for page, link in external_broken[:5]
                ]
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
