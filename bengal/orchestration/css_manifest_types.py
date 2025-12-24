"""
Type definitions for CSS manifest schema.

Provides TypedDict definitions for CSS manifest structure, enabling
type-safe loading and validation of theme CSS manifests.

Usage:
    from bengal.orchestration.css_manifest_types import CSSManifest

    manifest: CSSManifest = {
        "core": [...],
        "shared": [...],
        "type_map": {...},
        "feature_map": {...},
        "palettes": [...],
    }

See Also:
    - bengal/themes/default/css_manifest.py: Default theme manifest
    - bengal/orchestration/css_optimizer.py: Manifest consumer
"""

from __future__ import annotations

from typing import TypedDict


class CSSManifest(TypedDict, total=False):
    """
    Schema for CSS manifest structure.

    Attributes:
        core: CSS files always included (site won't render without these)
        shared: Common components used across most content types
        type_map: Content-type-specific CSS mapping
        feature_map: Feature-specific CSS mapping
        palettes: Color theme preset files
        experimental: Opt-in experimental CSS
        version: Manifest version for cache invalidation
    """

    core: list[str]
    shared: list[str]
    type_map: dict[str, list[str]]
    feature_map: dict[str, list[str]]
    palettes: list[str]
    experimental: list[str]
    version: int


class CSSOptimizationReport(TypedDict):
    """
    Report from CSS optimization process.

    Attributes:
        skipped: Whether optimization was skipped (no manifest)
        included_count: Number of CSS files included
        excluded_count: Number of CSS files excluded
        total_count: Total CSS files in manifest
        reduction_percent: Percentage reduction in file count
        types_detected: Content types detected in site
        features_detected: Features detected in site
        included_files: List of included CSS file paths
        excluded_files: List of excluded CSS file paths
    """

    skipped: bool
    included_count: int
    excluded_count: int
    total_count: int
    reduction_percent: int
    types_detected: list[str]
    features_detected: list[str]
    included_files: list[str]
    excluded_files: list[str]


