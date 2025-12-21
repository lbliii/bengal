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

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext


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
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Run URL collision validation checks."""
        results: list[CheckResult] = []

        # Track URLs and their sources
        urls_seen: dict[str, list[str]] = {}  # url -> [source1, source2, ...]

        for page in site.pages:
            url = page._path
            source = str(getattr(page, "source_path", page.title))

            if url not in urls_seen:
                urls_seen[url] = []
            urls_seen[url].append(source)

        # Report collisions
        collisions = {url: sources for url, sources in urls_seen.items() if len(sources) > 1}

        if collisions:
            # Format collision details with ownership context from registry
            details = []
            for url, sources in list(collisions.items())[:5]:  # Limit to first 5
                detail_lines = [f"URL: {url}"]

                # Get ownership context from registry if available
                claim = None
                if hasattr(site, "url_registry") and site.url_registry:
                    claim = site.url_registry.get_claim(url)

                for i, src in enumerate(sources):
                    owner_info = ""
                    if claim and i == 0:  # Show ownership for first source
                        owner_info = f" ({claim.owner}, priority {claim.priority})"
                    detail_lines.append(f"  Page {i + 1}: {src}{owner_info}")

                details.append("\n".join(detail_lines))

            results.append(
                CheckResult.error(
                    f"{len(collisions)} URL collision(s) detected - pages will overwrite each other",
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

        return results

    def _check_section_page_conflicts(self, site: Site) -> list[CheckResult]:
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
            if source.endswith("_index.md") or source.endswith("section-index.md"):
                continue

            if url in section_urls:
                conflicts.append((url, source))

        if conflicts:
            details = [f"{url}: {source}" for url, source in conflicts[:5]]
            results.append(
                CheckResult.warning(
                    f"{len(conflicts)} page(s) have same URL as a section",
                    recommendation=(
                        "Pages sharing a URL with a section may cause navigation issues. "
                        "Consider moving the page inside the section or using a different slug."
                    ),
                    details=details,
                )
            )

        return results
