"""
Taxonomy validator - checks tag pages and taxonomy integrity.

Validates:
- All tags have corresponding tag pages
- No orphaned tag pages
- Archive pages generated for sections
- Pagination works correctly
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext


class TaxonomyValidator(BaseValidator):
    """
    Validates taxonomy system integrity.

    Checks:
    - Tag pages generated for all tags
    - No orphaned tag pages (tag doesn't exist)
    - Archive pages exist for sections with content
    - Pagination pages are consistent
    """

    name = "Taxonomies"
    description = "Validates taxonomies: tags, categories, and generated pages"
    enabled_by_default = True

    @override
    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Run taxonomy validation checks."""
        results = []

        # Check 1: Tag page generation
        results.extend(self._check_tag_pages(site))

        # Check 2: Archive page generation
        results.extend(self._check_archive_pages(site))

        # Check 3: Taxonomy consistency
        results.extend(self._check_taxonomy_consistency(site))

        # Check 4: Pagination integrity
        results.extend(self._check_pagination(site))

        return results

    def _check_tag_pages(self, site: Site) -> list[CheckResult]:
        """Check that all tags have corresponding tag pages."""
        results = []

        if not site.taxonomies.get("tags"):
            results.append(
                CheckResult.info(
                    "No tags found in site",
                    recommendation="Add tags to page frontmatter to enable tag pages.",
                )
            )
            return results

        # Get all tags from taxonomy system
        tags = site.taxonomies["tags"]

        # Get all generated tag pages
        tag_pages = [
            p
            for p in site.pages
            if p.metadata.get("_generated") and p.metadata.get("type") == "tag"
        ]

        # Check if each tag has a page
        missing_tags = []
        for tag_slug, tag_data in tags.items():
            has_page = any(p.metadata.get("_tag_slug") == tag_slug for p in tag_pages)
            if not has_page:
                missing_tags.append(f"{tag_data['name']} ({tag_slug})")

        # Check for orphaned tag pages
        orphaned_pages = []
        for page in tag_pages:
            page_tag_slug: str | None = page.metadata.get("_tag_slug")
            if page_tag_slug and page_tag_slug not in tags:
                orphaned_pages.append(page_tag_slug)

        # Report results
        if missing_tags:
            results.append(
                CheckResult.error(
                    f"{len(missing_tags)} tag(s) have no generated pages",
                    recommendation="Check dynamic page generation in Site.generate_dynamic_pages()",
                    details=missing_tags[:5],
                )
            )
        elif orphaned_pages:
            # Treat orphaned tag pages as errors to surface misconfigurations prominently
            results.append(
                CheckResult.error(
                    f"{len(orphaned_pages)} orphaned tag page(s) found",
                    recommendation="These tag pages exist but their tags are not in the taxonomy.",
                    details=orphaned_pages[:5],
                )
            )
        else:
            results.append(
                CheckResult.success(
                    f"Tag pages validated ({len(tags)} tags, {len(tag_pages)} pages)"
                )
            )

        # Check for tag index page
        has_tag_index = any(p.metadata.get("type") == "tag-index" for p in site.pages)

        if tags and not has_tag_index:
            results.append(
                CheckResult.warning(
                    "No tag index page found",
                    recommendation="Site has tags but no /tags/ index page. Check Site._create_tag_index_page()",
                )
            )

        return results

    def _check_archive_pages(self, site: Site) -> list[CheckResult]:
        """Check that sections with content have archive pages."""
        results = []
        issues = []

        for section in site.sections:
            # Skip sections without pages (support tests using `children` instead of `pages`)
            section_pages = getattr(section, "pages", getattr(section, "children", []))
            if not section_pages:
                continue

            # Check if section has index page or archive
            has_index = section.index_page is not None
            # Accept either `_section` object ref (preferred) or `_section_url` metadata used in tests
            has_archive = any(
                p.metadata.get("_generated")
                and p.metadata.get("type") == "archive"
                and (
                    p.metadata.get("_section") == section
                    or (p.metadata.get("_section_url") == getattr(section, "href", None))
                )
                for p in site.pages
            )

            if not has_index and not has_archive:
                issues.append(
                    f"Section '{getattr(section, 'name', 'section')}' ({len(section_pages)} pages)"
                )

        if issues:
            results.append(
                CheckResult.warning(
                    f"{len(issues)} section(s) have content but no archive/index page",
                    recommendation="Sections should have _index.md or auto-generated archive pages.",
                    details=issues[:5],
                )
            )
        else:
            sections_with_content = sum(
                1
                for s in site.sections
                if getattr(s, "pages", getattr(s, "children", []))
                and getattr(s, "name", "") != "root"
            )
            results.append(
                CheckResult.success(f"Archive pages validated ({sections_with_content} sections)")
            )

        return results

    def _check_taxonomy_consistency(self, site: Site) -> list[CheckResult]:
        """Check taxonomy data consistency."""
        results = []
        issues = []

        # Check that taxonomy pages reference is consistent
        for taxonomy_type, terms in site.taxonomies.items():
            for term_slug, term_data in terms.items():
                # Check if pages listed in taxonomy actually have the tag
                pages_in_term = term_data.get("pages", [])

                for page in pages_in_term:
                    # For tags, check page.tags
                    if taxonomy_type == "tags":
                        if not hasattr(page, "tags") or not page.tags:
                            issues.append(
                                f"Page {page.source_path.name} in tag '{term_slug}' but has no tags"
                            )
                        elif term_data["name"] not in page.tags:
                            issues.append(
                                f"Page {page.source_path.name} in tag '{term_slug}' but tag not in page.tags"
                            )

                    # For categories, check page.metadata
                    elif taxonomy_type == "categories" and not page.metadata.get("category"):
                        issues.append(
                            f"Page {page.source_path.name} in category '{term_slug}' but has no category"
                        )

        if issues:
            results.append(
                CheckResult.error(
                    f"{len(issues)} taxonomy consistency issue(s)",
                    recommendation="This indicates a bug in taxonomy collection. Check Site.collect_taxonomies()",
                    details=issues[:5],
                )
            )
        else:
            total_terms = sum(len(terms) for terms in site.taxonomies.values())
            results.append(
                CheckResult.success(f"Taxonomy consistency validated ({total_terms} terms)")
            )

        return results

    def _check_pagination(self, site: Site) -> list[CheckResult]:
        """Check pagination integrity."""
        results = []
        issues = []

        # Find all pagination pages
        pagination_pages = [
            p for p in site.pages if p.metadata.get("_generated") and "/page/" in str(p.output_path)
        ]

        if not pagination_pages:
            results.append(
                CheckResult.info("No pagination pages found (all lists fit on single page)")
            )
            return results

        # Check pagination consistency
        for page in pagination_pages:
            paginator = page.metadata.get("_paginator")
            page_num = page.metadata.get("_page_num")

            if page.output_path is None:
                continue
            if not paginator:
                issues.append(f"{page.output_path.name}: No paginator in metadata")
            elif not page_num:
                issues.append(f"{page.output_path.name}: No page number in metadata")
            elif page_num > paginator.num_pages:
                issues.append(
                    f"{page.output_path.name}: Page {page_num} > total pages {paginator.num_pages}"
                )

        if issues:
            results.append(
                CheckResult.error(
                    f"{len(issues)} pagination issue(s)",
                    recommendation="Check pagination generation in Site.generate_dynamic_pages()",
                    details=issues[:5],
                )
            )
        else:
            results.append(
                CheckResult.success(
                    f"Pagination validated ({len(pagination_pages)} pagination pages)"
                )
            )

        return results
