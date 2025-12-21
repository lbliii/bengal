"""
Core domain models for Bengal SSG.

This package contains the foundational data models that represent
the content structure of a Bengal site:

Data Models:
    - Page: Individual content pages (complex model with mixins)
    - Section: Content groupings and hierarchy
    - Site: Top-level site container
    - Asset: Static assets (CSS, JS, images)
    - Menu: Navigation menus
    - Version: Documentation versioning support
    - NavTree: Pre-computed, cached navigation tree

Organization Pattern:
    - Simple models (< 400 lines): Single file (e.g., section.py)
    - Complex models (> 400 lines): Package (e.g., page/)

    When a model grows beyond 400 lines or requires multiple concerns,
    it should be converted to a package with focused modules/mixins.

Architecture:
    Core models are passive data structures with computed properties.
    They do not perform I/O, logging, or side effects. Operations on
    models are handled by orchestrators (see bengal/orchestration/).

Related:
    - Operations on models: bengal/orchestration/
    - Discovery of models: bengal/discovery/
    - Rendering of models: bengal/rendering/
    - Observability: Handled by orchestrators, not models

Example:
    >>> from bengal.core import Site, Page
    >>> site = Site(root_path=Path('.'))
    >>> page = Page(source_path=Path('content/post.md'))
"""

from __future__ import annotations

from bengal.core.asset import Asset
from bengal.core.menu import MenuBuilder, MenuItem
from bengal.core.nav_tree import NavNode, NavNodeProxy, NavTree, NavTreeCache, NavTreeContext
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site
from bengal.core.theme import Theme
from bengal.core.version import (
    GitBranchPattern,
    GitVersionConfig,
    Version,
    VersionConfig,
)

__all__ = [
    "Asset",
    "MenuBuilder",
    "MenuItem",
    "NavNode",
    "NavNodeProxy",
    "NavTree",
    "NavTreeCache",
    "NavTreeContext",
    "Page",
    "Section",
    "Site",
    "Theme",
    "Version",
    "VersionConfig",
]
