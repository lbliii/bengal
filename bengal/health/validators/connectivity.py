"""
Connectivity validator for knowledge graph analysis.

Validates site connectivity, identifies orphaned pages, over-connected hubs,
and provides insights for better content structure.
"""

from typing import TYPE_CHECKING, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


class ConnectivityValidator(BaseValidator):
    """
    Validates site connectivity using knowledge graph analysis.

    Checks:
    - Orphaned pages (no incoming references)
    - Over-connected hubs (too many incoming references)
    - Overall connectivity health
    - Content discovery issues

    This helps writers improve SEO, content discoverability, and site structure.
    """

    name = "Connectivity"
    description = "Analyzes page connectivity and finds orphaned or over-connected pages"
    enabled_by_default = True  # Enabled in dev profile

    @override
    def validate(self, site: "Site") -> list[CheckResult]:
        """
        Validate site connectivity.

        Args:
            site: The Site object being validated

        Returns:
            List of CheckResult objects with connectivity issues and recommendations
        """
        results = []

        # Import here to avoid circular dependency
        try:
            from bengal.analysis.knowledge_graph import KnowledgeGraph
        except ImportError as e:
            results.append(
                CheckResult.error(
                    "Knowledge graph analysis unavailable",
                    recommendation="Ensure bengal.analysis module is properly installed",
                    details=[str(e)],
                )
            )
            return results

        # Skip if no pages
        if not site.pages:
            results.append(CheckResult.info("No pages to analyze"))
            return results

        try:
            # Build knowledge graph
            logger.debug("connectivity_validator_start", total_pages=len(site.pages))

            graph = KnowledgeGraph(site)
            graph.build()

            metrics = graph.get_metrics()

            # Check 1: Orphaned pages
            orphans = graph.get_orphans()

            if orphans:
                # Get config threshold
                orphan_threshold = site.config.get("health_check", {}).get("orphan_threshold", 5)

                if len(orphans) > orphan_threshold:
                    # Too many orphans - error
                    results.append(
                        CheckResult.error(
                            f"{len(orphans)} pages have no incoming links (orphans)",
                            recommendation=(
                                "Add internal links, cross-references, or tags to connect orphaned pages. "
                                "Orphaned pages are hard to discover and may hurt SEO."
                            ),
                            details=[f"  • {p.source_path.name}" for p in orphans[:10]],
                        )
                    )
                elif len(orphans) > 0:
                    # Few orphans - warning
                    results.append(
                        CheckResult.warning(
                            f"{len(orphans)} orphaned page(s) found",
                            recommendation="Consider adding navigation or cross-references to these pages",
                            details=[f"  • {p.source_path.name}" for p in orphans[:5]],
                        )
                    )
            else:
                # No orphans - great!
                results.append(
                    CheckResult.success("No orphaned pages found - all pages are referenced")
                )

            # Check 2: Over-connected hubs
            super_hub_threshold = site.config.get("health_check", {}).get("super_hub_threshold", 50)
            hubs = graph.get_hubs(threshold=super_hub_threshold)

            if hubs:
                results.append(
                    CheckResult.info(
                        f"{len(hubs)} pages are heavily referenced (>{super_hub_threshold} refs)",
                        recommendation=(
                            "Consider splitting these pages into sub-topics for better navigation. "
                            "Very popular pages might benefit from multiple entry points."
                        ),
                        details=[
                            f"  • {p.title} ({graph.incoming_refs[id(p)]} refs)" for p in hubs[:5]
                        ],
                    )
                )

            # Check 3: Overall connectivity
            avg_connectivity = metrics.avg_connectivity

            if avg_connectivity < 1.0:
                results.append(
                    CheckResult.warning(
                        f"Low average connectivity ({avg_connectivity:.1f} links per page)",
                        recommendation=(
                            "Consider adding more internal links, cross-references, or tags. "
                            "Well-connected content is easier to discover and better for SEO."
                        ),
                    )
                )
            elif avg_connectivity >= 3.0:
                results.append(
                    CheckResult.success(
                        f"Good connectivity ({avg_connectivity:.1f} links per page)"
                    )
                )
            else:
                results.append(
                    CheckResult.info(
                        f"Moderate connectivity ({avg_connectivity:.1f} links per page)"
                    )
                )

            # Check 4: Hub distribution
            hub_percentage = (
                (metrics.hub_count / metrics.total_pages * 100) if metrics.total_pages > 0 else 0
            )

            if hub_percentage < 5:
                results.append(
                    CheckResult.info(
                        f"Only {hub_percentage:.1f}% of pages are hubs",
                        recommendation=(
                            "Consider creating more 'hub' pages that aggregate related content. "
                            "Index pages, topic overviews, and guides work well as hubs."
                        ),
                    )
                )

            # Summary info (without details since info() doesn't support it)
            results.append(
                CheckResult.info(
                    f"Analysis: {metrics.total_pages} pages, {metrics.total_links} links, "
                    f"{metrics.hub_count} hubs, {metrics.orphan_count} orphans, "
                    f"{metrics.avg_connectivity:.1f} avg connectivity"
                )
            )

            logger.debug(
                "connectivity_validator_complete",
                orphans=len(orphans),
                hubs=len(hubs),
                avg_connectivity=avg_connectivity,
            )

        except Exception as e:
            logger.error("connectivity_validator_error", error=str(e))
            results.append(
                CheckResult.error(
                    f"Connectivity analysis failed: {e!s}", recommendation="Check logs for details"
                )
            )

        return results
