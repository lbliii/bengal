"""
Ownership Policy Validator - validates that user content respects reserved namespaces.

Checks if content pages land in reserved namespaces (e.g., /tags/, autodoc prefixes,
special pages) and reports ownership violations separately from raw collisions.

See Also:
    - bengal.config.url_policy: Reserved namespace definitions
    - plan/drafted/plan-url-ownership-architecture.md: Implementation plan
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from bengal.config.url_policy import is_reserved_namespace
from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext


class OwnershipPolicyValidator(BaseValidator):
    """
    Validates that user content respects reserved namespace ownership.

    Checks if content pages land in reserved namespaces (e.g., /tags/, autodoc
    prefixes, special pages) and reports ownership violations separately from
    raw collisions. Warning mode by default (no build failure).

    Checks:
    - Content pages do not land in reserved namespaces
    - Reports ownership violations with namespace owner information
    - Provides clear guidance on namespace policy

    Example violation:
        Ownership violation: /tags/python/
          Content page: content/tags/python.md
          Reserved by: taxonomy (priority 40)
          Recommendation: Move content or use different slug
    """

    name = "Ownership Policy"
    description = "Validates that user content respects reserved namespace ownership"
    enabled_by_default = True

    @override
    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Run ownership policy validation checks."""
        results: list[CheckResult] = []

        violations: list[tuple[str, str, str]] = []  # (url, source, owner)

        # Check all pages for namespace violations
        for page in site.pages:
            url = getattr(page, "_path", None) or getattr(page, "href", "/")
            source = str(getattr(page, "source_path", page.title))

            # Skip generated pages (they're allowed in reserved namespaces)
            # Generated pages have virtual paths under .bengal/generated/
            if ".bengal/generated" in source or "__virtual__" in source:
                continue

            # Check if this URL falls in a reserved namespace
            is_reserved, owner = is_reserved_namespace(url, site.config)
            if is_reserved and owner:
                violations.append((url, source, owner))

        if violations:
            # Format violation details
            details = []
            for url, source, owner in violations[:10]:  # Limit to first 10
                details.append(f"URL: {url}\n  Content: {source}\n  Reserved by: {owner}")

            results.append(
                CheckResult.warning(
                    f"{len(violations)} ownership violation(s) detected - content in reserved namespaces",
                    recommendation=(
                        "User content should not be placed in reserved namespaces:\n"
                        "  - /tags/ (reserved for taxonomy)\n"
                        "  - /search/, /404.html, /graph/ (reserved for special pages)\n"
                        "  - Autodoc prefixes (reserved for autodoc output)\n"
                        "Fix: Move content to a different path or adjust slug."
                    ),
                    details=details,
                )
            )
        # No success message - if no violations, silence is golden

        return results
