"""Feature detection for CSS optimization during content discovery."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache


def _detect_features(orchestrator: Any, build_cache: BuildCache | None = None) -> None:
    """
    Detect CSS-requiring features in all pages.

    Scans page content for features that require specific CSS files:
    - mermaid: Mermaid diagram code blocks
    - data_tables: Tabulator/DataTable usage
    - graph: Graph/network visualization
    - interactive: Interactive widgets

    Populates site.features_detected for use by CSSOptimizer.

    Performance: O(n) scan over all pages, ~1ms per page.
    Thread-safe: Can be called from main thread during discovery.
    """
    from bengal.orchestration.feature_detector import FeatureDetector

    detector = FeatureDetector()

    for page in orchestrator.site.pages:
        cached_features = getattr(page, "_detected_features_cache", None)
        if cached_features:
            features = set(cached_features)
        elif getattr(page, "_from_cache", False) and build_cache is not None:
            facts = build_cache.get_parsed_discovery_facts(page.source_path)
            features = set(facts["detected_features"]) if facts else set()
        else:
            features = detector.detect_features_in_page(page)
        # Prefer BuildState (fresh each build), fall back to Site field
        _bs = orchestrator.site.build_state
        target = _bs.features_detected if _bs is not None else orchestrator.site.features_detected
        target.update(features)

    # Also check config for explicitly enabled features
    config = orchestrator.site.config
    _bs = orchestrator.site.build_state
    target = _bs.features_detected if _bs is not None else orchestrator.site.features_detected

    # Search enabled?
    if config.get("search", {}).get("enabled", False):
        target.add("search")

    # Graph enabled?
    if config.get("graph", {}).get("enabled", False):
        target.add("graph")
