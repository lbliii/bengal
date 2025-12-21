"""
Navigation validator - checks page navigation integrity.

Validates:
- next/prev chains work correctly
- Breadcrumb paths are valid
- Section navigation is consistent
- No broken navigation references
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext

logger = get_logger(__name__)


class NavigationValidator(BaseValidator):
    """
    Validates page navigation integrity.

    Checks:
    - next/prev links form valid chains
    - Breadcrumbs (ancestors) are valid
    - Section navigation is consistent
    - No orphaned pages in navigation
    """

    name = "Navigation"
    description = "Validates page navigation (next/prev, breadcrumbs, sections)"
    enabled_by_default = True

    @override
    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Run navigation validation checks."""
        results = []

        # Check 1: Next/prev chain integrity
        results.extend(self._check_next_prev_chains(site))

        # Check 2: Breadcrumb validity
        results.extend(self._check_breadcrumbs(site))

        # Check 3: Section navigation
        results.extend(self._check_section_navigation(site))

        # Check 4: Navigation coverage
        results.extend(self._check_navigation_coverage(site))

        # Check 5: Weight-based navigation (NEW - critical for docs)
        results.extend(self._check_weight_based_navigation(site))

        # Check 6: Output path completeness (NEW - critical for URLs)
        results.extend(self._check_output_path_completeness(site))

        return results

    def _check_next_prev_chains(self, site: Site) -> list[CheckResult]:
        """Check that next/prev links form valid chains."""
        results = []
        issues = []

        # Skip generated pages (they don't have next/prev in site collection)
        regular_pages = [p for p in site.pages if not p.metadata.get("_generated")]

        for page in regular_pages:
            # Check if next exists and points to valid page
            if hasattr(page, "next") and page.next:
                if page.next not in site.pages:
                    issues.append(f"{page.source_path.name}: page.next points to non-existent page")
                elif not page.next.output_path or not page.next.output_path.exists():
                    issues.append(
                        f"{page.source_path.name}: page.next points to page without output"
                    )

            # Check if prev exists and points to valid page
            if hasattr(page, "prev") and page.prev:
                if page.prev not in site.pages:
                    issues.append(f"{page.source_path.name}: page.prev points to non-existent page")
                elif not page.prev.output_path or not page.prev.output_path.exists():
                    issues.append(
                        f"{page.source_path.name}: page.prev points to page without output"
                    )

        if issues:
            results.append(
                CheckResult.error(
                    f"{len(issues)} page(s) have broken next/prev links",
                    recommendation="Check page navigation setup. This may indicate a bug in navigation system.",
                    details=issues[:5],
                )
            )
        else:
            results.append(
                CheckResult.success(f"Next/prev navigation validated ({len(regular_pages)} pages)")
            )

        return results

    def _check_breadcrumbs(self, site: Site) -> list[CheckResult]:
        """Check that breadcrumb trails (ancestors) are valid."""
        results = []
        issues = []

        for page in site.pages:
            # Skip pages without ancestors
            if not hasattr(page, "ancestors") or not page.ancestors:
                continue

            # Check each ancestor in the breadcrumb trail
            for i, ancestor in enumerate(page.ancestors):
                # Verify ancestor is a valid Section or Page
                # Sections don't have output_path, but they have 'name' and 'url' properties
                if not (hasattr(ancestor, "url") and hasattr(ancestor, "title")):
                    issues.append(
                        f"{page.source_path.name}: ancestor {i} is not a valid page/section"
                    )
                    continue

                # Validate ancestor exists in site's section tree when it looks like a Section
                try:
                    if getattr(ancestor, "href", None) and getattr(ancestor, "source_path", None):
                        # Consider it a Section-like object; verify membership by identity or URL
                        sections = getattr(site, "sections", []) or []
                        found = any(
                            (s is ancestor)
                            or (getattr(s, "href", None) == getattr(ancestor, "href", None))
                            for s in sections
                        )
                        if not found:
                            issues.append(
                                f"{page.source_path.name}: ancestor {i} not found in site.sections"
                            )
                except Exception as e:
                    logger.debug(
                        "health_navigation_breadcrumb_check_failed",
                        page=str(getattr(page, "source_path", "unknown")),
                        ancestor_index=i,
                        error=str(e),
                        error_type=type(e).__name__,
                        action="skipping_ancestor_check",
                    )

                # For Page ancestors (not Sections), check if they have output
                if (
                    hasattr(ancestor, "output_path")
                    and ancestor.output_path
                    and not ancestor.output_path.exists()
                ):
                    issues.append(
                        f"{page.source_path.name}: ancestor '{ancestor.title}' has no output"
                    )

        # If any breadcrumb ancestor is not found in sections, escalate to error
        if any("not found in site.sections" in d for d in issues):
            return [
                CheckResult.error(
                    f"{sum('not found in site.sections' in d for d in issues)} breadcrumb issue(s)",
                    recommendation="Ensure all breadcrumb ancestors correspond to real sections.",
                    details=[d for d in issues if "not found in site.sections" in d][:5],
                )
            ]

        if issues:
            results.append(
                CheckResult.warning(
                    f"{len(issues)} page(s) have invalid breadcrumb trails",
                    recommendation="Check section hierarchy and index pages.",
                    details=issues[:5],
                )
            )
        else:
            pages_with_breadcrumbs = sum(
                1 for p in site.pages if hasattr(p, "ancestors") and p.ancestors
            )
            results.append(
                CheckResult.success(
                    f"Breadcrumbs validated ({pages_with_breadcrumbs} pages with breadcrumbs)"
                )
            )

        return results

    def _check_section_navigation(self, site: Site) -> list[CheckResult]:
        """Check section-level navigation consistency."""
        results = []
        issues = []

        for section in site.sections:
            # Check if section has an index page or generated archive
            has_index = section.index_page is not None
            has_archive = any(
                p.metadata.get("_generated")
                and p.metadata.get("type") == "archive"
                and p.metadata.get("_section") == section
                for p in site.pages
            )

            # Some tests construct lightweight Section mocks that expose `children` but
            # not `pages`; support either for robustness in validation
            section_pages = getattr(section, "pages", getattr(section, "children", []))

            if not has_index and not has_archive and section_pages:
                issues.append(
                    f"Section '{getattr(section, 'name', 'section')}' has {len(section_pages)} pages but no index/archive"
                )

            # Check if section pages have proper parent reference
            for page in section_pages:
                if hasattr(page, "_section") and page._section != section:
                    issues.append(f"Page {page.source_path.name} has wrong section reference")

        if issues:
            results.append(
                CheckResult.warning(
                    f"{len(issues)} section navigation issue(s)",
                    recommendation="Sections with pages should have an _index.md or auto-generated archive page.",
                    details=issues[:5],
                )
            )
        else:
            results.append(
                CheckResult.success(f"Section navigation validated ({len(site.sections)} sections)")
            )

        return results

    def _check_navigation_coverage(self, site: Site) -> list[CheckResult]:
        """Check how many pages are reachable through navigation."""
        results = []

        # Count pages with navigation features
        regular_pages = [p for p in site.pages if not p.metadata.get("_generated")]

        with_next_prev = sum(
            1
            for p in regular_pages
            if (hasattr(p, "next") and p.next) or (hasattr(p, "prev") and p.prev)
        )
        with_breadcrumbs = sum(1 for p in regular_pages if hasattr(p, "ancestors") and p.ancestors)
        in_sections = sum(1 for p in regular_pages if hasattr(p, "_section") and p._section)

        # Calculate coverage
        total = len(regular_pages)
        if total > 0:
            next_prev_pct = (with_next_prev / total) * 100
            breadcrumb_pct = (with_breadcrumbs / total) * 100
            section_pct = (in_sections / total) * 100

            results.append(
                CheckResult.info(
                    f"Navigation coverage: {next_prev_pct:.0f}% next/prev, {breadcrumb_pct:.0f}% breadcrumbs, {section_pct:.0f}% in sections",
                    recommendation="High navigation coverage improves site usability."
                    if next_prev_pct < 80
                    else None,
                )
            )
        else:
            results.append(CheckResult.info("No regular pages to validate navigation coverage"))

        return results

    def _check_weight_based_navigation(self, site: Site) -> list[CheckResult]:
        """
        Check that weight-based navigation works correctly.

        For doc-type content, verifies:
        - next_in_section and prev_in_section respect weight order
        - Navigation stays within section boundaries
        - No cross-section jumps
        """
        results = []
        issues = []
        doc_types = {"doc", "tutorial", "autodoc-python", "autodoc-cli", "changelog"}

        # Check each section with doc-type content
        for section in site.sections:
            section_pages = getattr(section, "pages", getattr(section, "children", []))
            if not section_pages:
                continue

            # Check if section contains doc-type pages
            doc_pages = [
                p
                for p in section_pages
                if p.metadata.get("type") in doc_types
                and p.source_path.stem not in ("_index", "index")
            ]

            if not doc_pages:
                continue

            # Verify pages are sorted by weight
            sorted_pages = getattr(section, "sorted_pages", section_pages)
            non_index_pages = [
                p for p in sorted_pages if p.source_path.stem not in ("_index", "index")
            ]

            # Check navigation chain follows weight order
            for i, page in enumerate(non_index_pages):
                if i < len(non_index_pages) - 1:
                    # Check next_in_section
                    expected_next = non_index_pages[i + 1]
                    actual_next = page.next_in_section

                    if actual_next != expected_next:
                        issues.append(
                            f"Section '{section.name}': "
                            f"{page.title} next_in_section should be {expected_next.title}, "
                            f"got {actual_next.title if actual_next else 'None'}"
                        )

                if i > 0:
                    # Check prev_in_section
                    expected_prev = non_index_pages[i - 1]
                    actual_prev = page.prev_in_section

                    if actual_prev != expected_prev:
                        issues.append(
                            f"Section '{section.name}': "
                            f"{page.title} prev_in_section should be {expected_prev.title}, "
                            f"got {actual_prev.title if actual_prev else 'None'}"
                        )

        if issues:
            results.append(
                CheckResult.error(
                    f"{len(issues)} weight-based navigation issue(s)",
                    recommendation="This may indicate a bug in navigation system. "
                    "Check that next_in_section/prev_in_section use sorted_pages.",
                    details=issues[:5],
                )
            )
        else:
            doc_sections = sum(
                1
                for s in site.sections
                if any(
                    p.metadata.get("type") in doc_types
                    for p in getattr(s, "pages", getattr(s, "children", []))
                )
            )
            if doc_sections > 0:
                results.append(
                    CheckResult.success(
                        f"Weight-based navigation validated ({doc_sections} doc sections)"
                    )
                )

        return results

    def _check_output_path_completeness(self, site: Site) -> list[CheckResult]:
        """
        Check that all pages have output_path set.

        Critical for URL generation - pages without output_path
        will have incorrect URLs.
        """
        results = []
        missing = []

        for page in site.pages:
            if not page.output_path:
                missing.append(page.source_path.name)

        if missing:
            results.append(
                CheckResult.error(
                    f"{len(missing)} page(s) missing output_path",
                    recommendation="This is a critical bug. All pages should have output_path set during discovery. "
                    "Check ContentOrchestrator._set_output_paths() is being called.",
                    details=missing[:10],
                )
            )
        else:
            results.append(CheckResult.success(f"All {len(site.pages)} pages have output_path set"))

        return results
