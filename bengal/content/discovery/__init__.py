"""
Content and asset discovery for Bengal SSG.

This package provides the discovery layer that finds and organizes content files
and static assets during site builds.

Components:
ContentDiscovery: Discovers markdown/content files and organizes them into
    Page and Section hierarchies. Handles frontmatter parsing, i18n detection,
    collection validation, and symlink loop prevention.
AssetDiscovery: Finds static assets (images, CSS, JS) in the assets directory.
    Handles filtering of hidden/temporary files.

Architecture:
Discovery modules are responsible ONLY for finding and organizing content.
They do NOT perform rendering, writing, or other I/O operations beyond reading
source files. Build orchestrators in `bengal/orchestration/` coordinate the
full build workflow.

Discovery uses parallel processing (ThreadPoolExecutor) for performance when
parsing large content directories. Content caching through BuildContext
eliminates redundant disk I/O during health checks.

Related:
- bengal/core/page/: Page and PageProxy data models
- bengal/core/section.py: Section data model
- bengal/content/versioning/: Version discovery and resolution
- bengal/orchestration/: Build orchestration that uses discovery
- bengal/health/: Validators that consume cached content from discovery

Example:
    >>> from bengal.content.discovery import ContentDiscovery, AssetDiscovery
    >>> from pathlib import Path
    >>>
    >>> # Discover content
    >>> content_discovery = ContentDiscovery(Path("content"))
    >>> sections, pages = content_discovery.discover()
    >>>
    >>> # Discover assets
    >>> asset_discovery = AssetDiscovery(Path("assets"))
    >>> assets = asset_discovery.discover()

"""

from __future__ import annotations

from bengal.content.discovery.asset_discovery import AssetDiscovery
from bengal.content.discovery.content_discovery import ContentDiscovery

__all__ = ["AssetDiscovery", "ContentDiscovery"]
