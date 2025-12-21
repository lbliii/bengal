"""
Health check validators for Bengal SSG.

Each validator checks a specific aspect of the build:

Phase 1 (Basic):
- OutputValidator: Page sizes, asset presence
- ConfigValidator: Configuration validity (integrates existing validator)
- MenuValidator: Menu structure integrity
- LinkValidator: Broken links detection

Phase 2 (Build-Time):
- NavigationValidator: Page navigation (next/prev, breadcrumbs)
- TaxonomyValidator: Tags, categories, generated pages
- RenderingValidator: HTML quality, template functions
- DirectiveValidator: Directive syntax, usage, and performance

Phase 3 (Advanced):
- CacheValidator: Incremental build cache integrity
- PerformanceValidator: Build performance metrics

Phase 4 (Production-Ready):
- RSSValidator: RSS feed quality and completeness
- SitemapValidator: Sitemap.xml validity for SEO
- FontValidator: Font downloads and CSS generation
- AssetValidator: Asset optimization and integrity

Phase 5 (Knowledge Graph):
- ConnectivityValidator: Page connectivity and orphan detection
"""

from __future__ import annotations

from bengal.health.validators.anchors import AnchorValidator
from bengal.health.validators.assets import AssetValidator
from bengal.health.validators.cache import CacheValidator
from bengal.health.validators.config import ConfigValidatorWrapper
from bengal.health.validators.connectivity import ConnectivityValidator
from bengal.health.validators.cross_ref import CrossReferenceValidator
from bengal.health.validators.directives import DirectiveValidator
from bengal.health.validators.fonts import FontValidator
from bengal.health.validators.links import LinkValidator, LinkValidatorWrapper, validate_links
from bengal.health.validators.menu import MenuValidator
from bengal.health.validators.navigation import NavigationValidator
from bengal.health.validators.output import OutputValidator
from bengal.health.validators.performance import PerformanceValidator
from bengal.health.validators.rendering import RenderingValidator
from bengal.health.validators.rss import RSSValidator
from bengal.health.validators.sitemap import SitemapValidator
from bengal.health.validators.taxonomy import TaxonomyValidator
from bengal.health.validators.templates import TemplateValidator, validate_templates
from bengal.health.validators.tracks import TrackValidator
from bengal.health.validators.url_collisions import URLCollisionValidator

__all__ = [
    # Anchor validation (RFC: plan/active/rfc-explicit-anchor-targets.md)
    "AnchorValidator",
    "AssetValidator",
    # Phase 3
    "CacheValidator",
    "ConfigValidatorWrapper",
    # Phase 5
    "ConnectivityValidator",
    # Cross-reference validation
    "CrossReferenceValidator",
    "DirectiveValidator",
    "FontValidator",
    # Link validation (consolidated from rendering/)
    "LinkValidator",
    "LinkValidatorWrapper",
    "MenuValidator",
    # Phase 2
    "NavigationValidator",
    # Phase 1
    "OutputValidator",
    "PerformanceValidator",
    # Phase 4
    "RSSValidator",
    "RenderingValidator",
    "SitemapValidator",
    "TaxonomyValidator",
    # Template validation (consolidated from rendering/)
    "TemplateValidator",
    "TrackValidator",
    # URL collision detection (RFC: plan/drafted/rfc-url-collision-detection.md)
    "URLCollisionValidator",
    # Convenience functions
    "validate_links",
    "validate_templates",
]
