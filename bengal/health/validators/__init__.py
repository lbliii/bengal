"""
Health check validators for Bengal SSG.

Each validator inherits from BaseValidator and checks a specific aspect of
site health. Validators are organized by deployment phase and complexity.

Phase 1 - Basic Validation:
    OutputValidator: Page sizes, asset presence, output structure
    ConfigValidatorWrapper: Configuration validity (wraps config.validate)
    MenuValidator: Menu structure, item ordering, internal link validity
    LinkValidator: Broken links detection (internal and external)

Phase 2 - Build-Time Validation:
    NavigationValidator: Page navigation (next/prev links, breadcrumbs)
    TaxonomyValidator: Tags, categories, and generated taxonomy pages
    RenderingValidator: HTML quality, template function usage
    DirectiveValidator: MyST directive syntax, nesting, and performance

Phase 3 - Advanced Validation:
    CacheValidator: Incremental build cache integrity
    PerformanceValidator: Build performance metrics and thresholds

Phase 4 - Production-Ready Validation:
    RSSValidator: RSS/Atom feed quality and schema compliance
    SitemapValidator: sitemap.xml validity for SEO
    FontValidator: Font downloads, subsetting, and CSS generation
    AssetValidator: Asset optimization, integrity, and caching headers

Phase 5 - Knowledge Graph Validation:
    ConnectivityValidator: Page connectivity graph and orphan detection
    AnchorValidator: Explicit anchor targets and cross-reference integrity
    CrossReferenceValidator: Internal cross-reference resolution
    TrackValidator: Learning track structure and progression

Specialized Validators:
    AutodocValidator: API documentation HTML structure validation
    OwnershipPolicyValidator: URL ownership and content governance
    URLCollisionValidator: Duplicate URL detection
    TemplateValidator: Jinja2 template syntax and best practices

Usage:
    Validators are registered with HealthCheck orchestrator and run via CLI:

    >>> bengal health check --validators output,links,directives
    >>> bengal health check --tier build  # Run all build-tier validators

See Also:
    - bengal.health.base.BaseValidator: Abstract base class
    - bengal.health.health_check.HealthCheck: Orchestrator
    - bengal.cli.health: CLI commands
"""

from __future__ import annotations

from bengal.health.validators.anchors import AnchorValidator
from bengal.health.validators.assets import AssetValidator
from bengal.health.validators.autodoc import AutodocValidator
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
from bengal.health.validators.ownership_policy import OwnershipPolicyValidator
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
    # Autodoc HTML validation
    "AutodocValidator",
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
    # Ownership policy validation (RFC: plan/drafted/plan-url-ownership-architecture.md)
    "OwnershipPolicyValidator",
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
