"""
Link validator wrapper.

Integrates the existing LinkValidator into the health check system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.core.site import Site


class LinkValidatorWrapper(BaseValidator):
    """
    Wrapper for link validation.

    Note: Link validation runs during post-processing. This validator
    re-runs validation or reports on previous validation results.
    """

    name = "Links"
    description = "Validates internal and external links"
    enabled_by_default = True

    @override
    def validate(self, site: Site) -> list[CheckResult]:
        """Validate links in generated pages."""
        results = []

        # Only run if link validation is enabled
        if not site.config.get("validate_links", True):
            results.append(CheckResult.info("Link validation disabled in config"))
            return results

        # Run link validator
        from bengal.rendering.link_validator import LinkValidator

        validator = LinkValidator()
        broken_links = validator.validate_site(site)

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

            if internal_broken:
                # Format as "page: link" for display
                details = [f"{page}: {link}" for page, link in internal_broken[:5]]
                results.append(
                    CheckResult.error(
                        f"{len(internal_broken)} broken internal link(s)",
                        recommendation="Fix broken internal links. They point to pages that don't exist.",
                        details=details,
                    )
                )

            if external_broken:
                details = [f"{page}: {link}" for page, link in external_broken[:5]]
                results.append(
                    CheckResult.warning(
                        f"{len(external_broken)} broken external link(s)",
                        recommendation="External links may be temporarily unavailable or incorrect.",
                        details=details,
                    )
                )
        else:
            results.append(CheckResult.success("All links are valid"))

        return results
