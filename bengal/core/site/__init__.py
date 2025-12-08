"""
Site package for Bengal SSG.

This package provides the Site class - the central container for all content
(pages, sections, assets) and the coordinator of the build process.

Public API:
    - Site: Main site dataclass with discovery, build, and serve capabilities

The Site class is composed of several focused mixins:
    - SitePropertiesMixin: Configuration property accessors
    - PageCachesMixin: Cached page lists (regular_pages, generated_pages, etc.)
    - SiteFactoriesMixin: Factory methods (from_config, for_testing)
    - ContentDiscoveryMixin: Content and asset discovery
    - ThemeIntegrationMixin: Theme resolution and asset chain
    - DataLoadingMixin: Data directory loading
    - SectionRegistryMixin: O(1) section lookups

Usage:
    from bengal.core.site import Site

    # From configuration (recommended):
    site = Site.from_config(Path('/path/to/site'))

    # For testing:
    site = Site.for_testing()

    # Direct instantiation (advanced):
    site = Site(root_path=Path('/path'), config={})

Related Modules:
    - bengal.orchestration.build: Build orchestration
    - bengal.rendering.template_engine: Template rendering
    - bengal.cache.build_cache: Build state persistence
"""

from __future__ import annotations

from bengal.core.site.core import Site

__all__ = [
    "Site",
]

