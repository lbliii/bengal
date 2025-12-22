"""
Site package for Bengal SSG.

Provides the Site class—the central container for all content (pages,
sections, assets) and coordinator of the build process.

Public API:
    Site: Main site dataclass with discovery, build, and serve capabilities

Creation:
    Site.from_config(path): Load from bengal.toml (recommended)
    Site.for_testing(): Minimal instance for unit tests
    Site(root_path, config): Direct instantiation (advanced)

Package Structure:
    core.py: Site dataclass with build/serve methods
    properties.py: SitePropertiesMixin (config accessors)
    page_caches.py: PageCachesMixin (cached page lists)
    factories.py: SiteFactoriesMixin (from_config, for_testing)
    discovery.py: ContentDiscoveryMixin (content/asset discovery)
    theme.py: ThemeIntegrationMixin (theme resolution)
    data.py: DataLoadingMixin (data/ directory)
    section_registry.py: SectionRegistryMixin (O(1) section lookups)

Key Features:
    Build Coordination: site.build() orchestrates full build pipeline
    Dev Server: site.serve() starts live-reload development server
    Content Discovery: site.discover_content() finds pages/sections/assets
    Theme Resolution: site.theme_config provides theme configuration
    Query Interface: site.pages, site.sections, site.taxonomies

Example:
    from bengal.core import Site

    site = Site.from_config(Path('/path/to/site'))
    site.build(parallel=True, incremental=True)

Related Packages:
    bengal.orchestration.build: Build orchestration
    bengal.rendering.template_engine: Template rendering
    bengal.cache.build_cache: Build state persistence
"""

from __future__ import annotations

from bengal.core.site.core import Site

__all__ = [
    "Site",
]
