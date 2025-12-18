"""
Connectivity validator for knowledge graph analysis.

Validates site connectivity using semantic link model and connectivity levels,
identifies isolated pages, and provides insights for better content structure.

Uses weighted scoring based on link types:
- EXPLICIT: Human-authored markdown links (weight: 1.0)
- MENU: Navigation menu items (weight: 10.0)
- TAXONOMY: Shared tags/categories (weight: 1.0)
- RELATED: Algorithm-computed related posts (weight: 0.75)
- TOPICAL: Section hierarchy parent → child (weight: 0.5)
- SEQUENTIAL: Next/prev navigation (weight: 0.25)

Connectivity Levels:
- WELL_CONNECTED: Score >= 2.0 (no action needed)
- ADEQUATELY_LINKED: Score 1.0-2.0 (could improve)
- LIGHTLY_LINKED: Score 0.25-1.0 (should improve)
- ISOLATED: Score < 0.25 (needs attention)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext

logger = get_logger(__name__)

# Exposed for test patching; will be bound on first validate() call
KnowledgeGraph = None  # type: ignore


class ConnectivityValidator(BaseValidator):
    """
    Validates site connectivity using semantic link model and knowledge graph analysis.

    Checks:
    - Isolated pages (weighted score < 0.25)
    - Lightly linked pages (score 0.25-1.0, only structural links)
    - Over-connected hubs (too many incoming references)
    - Overall connectivity health (average weighted score)
    - Content discovery issues

    Uses weighted scoring based on link types (explicit, menu, taxonomy, etc.)
    to provide nuanced analysis beyond binary orphan detection.

    This helps writers improve SEO, content discoverability, and site structure.
    """

    name = "Connectivity"
    description = "Analyzes page connectivity using semantic link model and connectivity levels"
    enabled_by_default = True  # Enabled in dev profile

    @override
    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """
        Validate site connectivity.

        Args:
            site: The Site object being validated
            build_context: Optional BuildContext with cached knowledge graph

        Returns:
            List of CheckResult objects with connectivity issues and recommendations
        """
        results = []

        # Import here to avoid circular dependency, but keep a module-level alias
        # so tests can monkeypatch bengal.health.validators.connectivity.KnowledgeGraph
        global KnowledgeGraph  # type: ignore
        try:
            # Respect pre-patched symbol from tests; only import if not set
            if KnowledgeGraph is None:  # type: ignore
                from bengal.analysis.knowledge_graph import KnowledgeGraph as _KG  # local alias

                KnowledgeGraph = _KG  # expose for test patching
        except ImportError as e:  # pragma: no cover - exercised by tests
            # Mirror tests: return an error mentioning "unavailable"
            msg = "Knowledge graph analysis unavailable"
            results.append(
                CheckResult.error(
                    msg,
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
            # Try to get cached graph from build context first
            graph = None
            if build_context is not None:
                graph = getattr(build_context, "knowledge_graph", None)
                if graph is not None:
                    logger.debug(
                        "connectivity_validator_using_cached_graph",
                        total_pages=len(site.pages),
                    )

            # Fallback: build our own (for standalone health check)
            if graph is None:
                logger.debug("connectivity_validator_start", total_pages=len(site.pages))
                try:
                    graph = KnowledgeGraph(site)  # type: ignore[operator]
                except ImportError as e:  # Align behavior with import-path failure for tests
                    msg = "Knowledge graph analysis unavailable"
                    results.append(
                        CheckResult.error(
                            msg,
                            recommendation="Ensure bengal.analysis module is properly installed",
                            details=[str(e)],
                        )
                    )
                    return results
                graph.build()

            # Normalize helpers to be robust to mocks
            def _normalize_hubs(h: list[Page] | list[tuple[Page, int]] | None) -> list[Page]:
                # Accept list[Page] or list[tuple[Page,int]]
                normalized: list[Page] = []
                try:
                    for item in h or []:
                        if isinstance(item, tuple) and len(item) >= 1:
                            normalized.append(item[0])
                        else:
                            normalized.append(item)
                except Exception as e:
                    logger.debug(
                        "health_connectivity_hub_normalize_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                        action="returning_empty_list",
                    )
                    return []
                return normalized

            def _safe_get_metrics() -> dict[str, Any]:
                try:
                    m = graph.get_metrics()
                    if isinstance(m, dict):
                        return {
                            "total_pages": m.get("nodes", 0),
                            "total_links": m.get("edges", 0),
                            "avg_connectivity": float(m.get("average_degree", 0.0) or 0.0),
                            "hub_count": 0,
                            "orphan_count": 0,
                        }
                    # object-like
                    return {
                        "total_pages": getattr(m, "total_pages", 0) or 0,
                        "total_links": getattr(m, "total_links", 0) or 0,
                        "avg_connectivity": float(getattr(m, "avg_connectivity", 0.0) or 0.0),
                        "hub_count": getattr(m, "hub_count", 0) or 0,
                        "orphan_count": getattr(m, "orphan_count", 0) or 0,
                    }
                except Exception as e:
                    logger.debug(
                        "health_connectivity_metrics_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                        action="using_fallback_metrics",
                    )
                    return {
                        "total_pages": len(getattr(site, "pages", []) or []),
                        "total_links": 0,
                        "avg_connectivity": 0.0,
                        "hub_count": 0,
                        "orphan_count": 0,
                    }

            metrics = _safe_get_metrics()

            # Check 1: Connectivity levels using semantic link model
            try:
                connectivity_report = graph.get_connectivity_report()
                dist = connectivity_report.get_distribution()
                pct = connectivity_report.get_percentages()
                isolated_pages = connectivity_report.isolated
                lightly_linked_pages = connectivity_report.lightly_linked
            except Exception as e:
                logger.debug(
                    "health_connectivity_report_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    action="falling_back_to_legacy_orphan_check",
                )
                # Fallback to legacy orphan detection
                try:
                    orphans = list(graph.get_orphans() or [])
                except Exception:
                    orphans = []
                isolated_pages = orphans
                lightly_linked_pages = []
                dist = {
                    "lightly_linked": 0,
                    "adequately_linked": 0,
                    "well_connected": 0,
                }
                pct = {
                    "isolated": 0.0,
                    "lightly_linked": 0.0,
                    "adequately_linked": 0.0,
                    "well_connected": 0.0,
                }
                connectivity_report = None

            # Get config thresholds
            health_config = site.config.get("health_check", {})
            isolated_threshold = health_config.get(
                "isolated_threshold", health_config.get("orphan_threshold", 5)
            )
            lightly_linked_threshold = health_config.get("lightly_linked_threshold", 20)

            # Check 1a: Isolated pages (score < 0.25)
            if isolated_pages:
                if len(isolated_pages) > isolated_threshold:
                    # Too many isolated - error
                    results.append(
                        CheckResult.error(
                            f"{len(isolated_pages)} isolated pages (score < 0.25)",
                            recommendation=(
                                "Add explicit cross-references or internal links to connect isolated pages. "
                                "Isolated pages have no meaningful connections and are hard to discover."
                            ),
                            details=[
                                f"  🔴 {getattr(p.source_path, 'name', str(p))}"
                                for p in isolated_pages[:10]
                            ],
                        )
                    )
                else:
                    # Few isolated - warning
                    results.append(
                        CheckResult.warning(
                            f"{len(isolated_pages)} isolated page(s) found",
                            recommendation="Consider adding navigation or cross-references to these pages",
                            details=[
                                f"  🔴 {getattr(p.source_path, 'name', str(p))}"
                                for p in isolated_pages[:5]
                            ],
                        )
                    )
            else:
                # No isolated - great!
                results.append(
                    CheckResult.success("No isolated pages - all pages have meaningful connections")
                )

            # Check 1b: Lightly linked pages (score 0.25-1.0)
            if lightly_linked_pages:
                if len(lightly_linked_pages) > lightly_linked_threshold:
                    results.append(
                        CheckResult.warning(
                            f"{len(lightly_linked_pages)} lightly-linked pages (score 0.25-1.0)",
                            recommendation=(
                                "These pages rely on structural links only. "
                                "Add explicit cross-references to improve discoverability."
                            ),
                            details=[
                                f"  🟠 {getattr(p.source_path, 'name', str(p))}"
                                for p in lightly_linked_pages[:5]
                            ],
                        )
                    )
                else:
                    results.append(
                        CheckResult.info(
                            f"{len(lightly_linked_pages)} lightly-linked page(s) could use more connections"
                        )
                    )

            # Check 2: Over-connected hubs (robust to mocked shapes)
            hubs = []
            try:
                super_hub_threshold = site.config.get("health_check", {}).get(
                    "super_hub_threshold", 50
                )
                hubs = _normalize_hubs(graph.get_hubs(threshold=super_hub_threshold))
                if hubs:
                    results.append(
                        CheckResult.warning(
                            f"{len(hubs)} hub page(s) detected (>{super_hub_threshold} refs)",
                            recommendation=(
                                "Consider splitting these pages into sub-topics for better navigation. "
                                "Very popular pages might benefit from multiple entry points."
                            ),
                        )
                    )
            except Exception as e:
                logger.debug(
                    "health_connectivity_hub_detection_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    action="skipping_hub_check",
                )
                hubs = []

            # Check 3: Overall connectivity (using weighted score if available)
            avg_connectivity = metrics.get("avg_connectivity", 0.0)
            avg_score = connectivity_report.avg_score if connectivity_report else 0.0

            # Use weighted score for more nuanced assessment
            if avg_score > 0:
                if avg_score < 1.0:
                    results.append(
                        CheckResult.warning(
                            f"Low average connectivity score ({avg_score:.2f})",
                            recommendation=(
                                "Consider adding more internal links, cross-references, or tags. "
                                "Aim for an average score >= 1.0 for good discoverability."
                            ),
                        )
                    )
                elif avg_score >= 2.0:
                    results.append(
                        CheckResult.success(f"Good connectivity score ({avg_score:.2f})")
                    )
                else:
                    results.append(
                        CheckResult.info(f"Moderate connectivity score ({avg_score:.2f})")
                    )
            else:
                # Fallback to legacy metric
                if avg_connectivity <= 1.0:
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

            # Check 4: Hub distribution (best-effort)
            try:
                total_pages = metrics.get("total_pages", 0)
                hub_count = len(hubs) if hubs else metrics.get("hub_count", 0)
                hub_percentage = (hub_count / total_pages * 100) if total_pages else 0
            except Exception as e:
                logger.debug(
                    "health_connectivity_hub_percentage_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    action="using_zero_percentage",
                )
                hub_percentage = 0

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

            # Summary info with connectivity distribution
            import contextlib

            with contextlib.suppress(Exception):
                results.append(
                    CheckResult.info(
                        f"Analysis: {metrics.get('total_pages', 0)} pages | "
                        f"🟢 {dist.get('well_connected', 0)} well | "
                        f"🟡 {dist.get('adequately_linked', 0)} adequate | "
                        f"🟠 {dist.get('lightly_linked', 0)} lightly | "
                        f"🔴 {dist.get('isolated', 0)} isolated | "
                        f"Score: {avg_score:.2f}"
                    )
                )

            logger.debug(
                "connectivity_validator_complete",
                isolated=len(isolated_pages),
                lightly_linked=len(lightly_linked_pages),
                hubs=len(hubs),
                avg_score=avg_score,
                distribution=dist,
            )

        except ImportError as e:
            # Catch late ImportError (e.g., patched KnowledgeGraph raising ImportError on call)
            msg = "Knowledge graph analysis unavailable"
            results.append(
                CheckResult.error(
                    msg,
                    recommendation="Ensure bengal.analysis module is properly installed",
                    details=[str(e)],
                )
            )
            return results
        except Exception as e:
            logger.error("connectivity_validator_error", error=str(e))
            results.append(
                CheckResult.error(
                    f"Connectivity analysis failed: {e!s}", recommendation="Check logs for details"
                )
            )

        return results
