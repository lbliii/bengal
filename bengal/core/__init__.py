"""
Core domain models for Bengal SSG.

This package provides the foundational data models representing
the content structure of a Bengal site. All models are passive
data structures—they do not perform I/O, logging, or side effects.

Public API:
    Site: Top-level site container coordinating pages, sections, and assets
    Page: Individual content page with metadata, content, and rendering state
    Section: Hierarchical content grouping (directories in content tree)
    Asset: Static file (CSS, JS, images, fonts) with processing capabilities
    Theme: Theme configuration accessible as site.theme in templates

Navigation:
    MenuBuilder: Constructs hierarchical menu structures from config/pages
    MenuItem: Single menu item with optional children and active state
    NavTree: Pre-computed navigation tree with O(1) lookups
    NavNode: Navigation tree node with URL, title, and children
    NavNodeProxy: Template-safe proxy that applies baseurl to URLs
    NavTreeContext: Per-page context for active trail detection
    NavTreeCache: Thread-safe cache for NavTree instances

Versioning:
    Version: Single documentation version (e.g., v3, v2)
    VersionConfig: Site-wide versioning configuration
    GitVersionConfig: Git-based version discovery configuration
    GitBranchPattern: Pattern matching for Git branches/tags

Architecture:
    Core models are passive data structures with computed properties.
    They do not perform I/O, logging, or side effects. Operations on
    models are handled by orchestrators (see bengal/orchestration/).

    Organization Pattern:
    - Simple models (< 400 lines): Single file (e.g., section.py)
    - Complex models (> 400 lines): Package (e.g., page/, site/)

Related Packages:
    bengal.orchestration: Build operations and coordination
    bengal.discovery: Content and asset discovery
    bengal.rendering: Template and content rendering
    bengal.cache: Build state caching

Example:
    >>> from bengal.core import Site, Page, Section
    >>> site = Site.from_config(Path('/path/to/site'))
    >>> page = Page(source_path=Path('content/post.md'))
    >>> section = site.get_section_by_name('blog')
"""

from __future__ import annotations

from bengal.core.asset import Asset
from bengal.core.menu import MenuBuilder, MenuItem
from bengal.core.nav_tree import NavNode, NavNodeProxy, NavTree, NavTreeCache, NavTreeContext
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site
from bengal.core.theme import Theme
from bengal.core.url_ownership import URLClaim, URLCollisionError, URLRegistry
from bengal.core.version import (
    GitBranchPattern,
    GitVersionConfig,
    Version,
    VersionConfig,
)

__all__ = [
    # Primary models
    "Asset",
    "Page",
    "Section",
    "Site",
    "Theme",
    # Navigation
    "MenuBuilder",
    "MenuItem",
    "NavNode",
    "NavNodeProxy",
    "NavTree",
    "NavTreeCache",
    "NavTreeContext",
    # Versioning
    "GitBranchPattern",
    "GitVersionConfig",
    "Version",
    "VersionConfig",
    # URL ownership
    "URLClaim",
    "URLCollisionError",
    "URLRegistry",
]
