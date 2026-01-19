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

Architecture (RFC: Aggressive Cleanup):
Site is now a unified dataclass with all functionality inlined:
- Properties: Config accessors (title, baseurl, author, etc.)
- Page Caches: Cached page lists (regular_pages, generated_pages, etc.)
- Content Discovery: discover_content(), discover_assets()
- Data Loading: _load_data_directory()
- Section Registry: O(1) section lookups via registry

Factory Methods:
from_config() and for_testing() are classmethods on Site.

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

from bengal.core.site.core import Site

__all__ = [
    "Site",
]
