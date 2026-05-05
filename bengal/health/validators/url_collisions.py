"""
URL collision validator - detects when multiple pages output to the same URL.

Validates:
- No duplicate URLs among pages
- No section/page URL conflicts
- Clear collision reporting with source identification

See Also:
- plan/drafted/rfc-url-collision-detection.md: Design rationale

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from bengal.core.url_collisions import collect_url_collision_records
from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext
    from bengal.protocols import SiteLike


class URLCollisionValidator(BaseValidator):
    """
    Validates that no two pages output to the same URL.

    URL collisions cause silent overwrites where the last page to render
    wins, resulting in broken navigation and lost content. This was the
    root cause of the CLI navigation bug where the root command page
    overwrote the section index.

    Checks:
    - No duplicate URLs among site.pages
    - Reports all collisions with source file information
    - Provides actionable fix recommendations

    Example collision:
        URL collision: /cli/
          Page 1: __virtual__/cli/section-index.md
          Page 2: cli.md

    Priority:
        This validator runs during health checks and catches collisions
        that may have occurred if proactive validation was bypassed.

    """

    name = "URL Collisions"
    description = "Detects when multiple pages output to the same URL"
    enabled_by_default = True

    @override
    def validate(
        self, site: SiteLike, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Run URL collision validation checks."""
        results: list[CheckResult] = []

        collisions = collect_url_collision_records(
            site.pages,
            root_path=getattr(site, "root_path", None),
            url_registry=getattr(site, "url_registry", None),
        )

        if collisions:
            # Format collision details with ownership context from registry
            details = []
            for collision in collisions[:5]:  # Limit to first 5
                detail_lines = [f"URL: {collision.url}"]

                for i, claimant in enumerate(collision.claimants):
                    owner_info = (
                        f" ({claimant.owner}, priority {claimant.priority})"
                        if claimant.owner
                        else ""
                    )
                    detail_lines.append(f"  Page {i + 1}: {claimant.display_source}{owner_info}")

                details.append("\n".join(detail_lines))

            results.append(
                CheckResult.error(
                    f"{len(collisions)} URL collision(s) detected - pages will overwrite each other",
                    code="H020",
                    recommendation=(
                        "Each page must have a unique URL. Common causes:\n"
                        "  1. Duplicate slugs in frontmatter\n"
                        "  2. Autodoc section index conflicting with autodoc page\n"
                        "  3. Manual content at same path as generated content\n"
                        "Fix: Rename one page or adjust its slug/output path."
                    ),
                    details=details,
                )
            )
        # No success message - if no collisions, silence is golden

        # Check for section/page URL conflicts
        results.extend(self._check_section_page_conflicts(site))

        return results

    def _check_section_page_conflicts(self, site: SiteLike) -> list[CheckResult]:
        """
        Check for conflicts between sections and pages at the same URL.

        A section's index page and a standalone page at the same URL is
        a common source of navigation issues.
        """
        results: list[CheckResult] = []

        # Build set of section URLs
        section_urls = {s._path for s in site.sections}

        # Find pages that conflict with sections
        conflicts = []
        for page in site.pages:
            url = page._path
            source = str(getattr(page, "source_path", page.title))

            # Skip index pages - they're supposed to be at section URLs
            if source.endswith(("_index.md", "section-index.md")):
                continue

            if url in section_urls:
                conflicts.append((url, source))

        if conflicts:
            details = [f"{url}: {source}" for url, source in conflicts[:5]]
            results.append(
                CheckResult.warning(
                    f"{len(conflicts)} page(s) have same URL as a section",
                    code="H021",
                    recommendation=(
                        "Pages sharing a URL with a section may cause navigation issues. "
                        "Consider moving the page inside the section or using a different slug."
                    ),
                    details=details,
                )
            )

        return results
