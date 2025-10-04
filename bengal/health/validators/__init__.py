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

Phase 3 Lite (Advanced):
- CacheValidator: Incremental build cache integrity
- PerformanceValidator: Build performance metrics
"""

from bengal.health.validators.output import OutputValidator
from bengal.health.validators.config import ConfigValidatorWrapper
from bengal.health.validators.menu import MenuValidator
from bengal.health.validators.links import LinkValidatorWrapper
from bengal.health.validators.navigation import NavigationValidator
from bengal.health.validators.taxonomy import TaxonomyValidator
from bengal.health.validators.rendering import RenderingValidator
from bengal.health.validators.directives import DirectiveValidator
from bengal.health.validators.cache import CacheValidator
from bengal.health.validators.performance import PerformanceValidator

__all__ = [
    # Phase 1
    'OutputValidator',
    'ConfigValidatorWrapper',
    'MenuValidator',
    'LinkValidatorWrapper',
    # Phase 2
    'NavigationValidator',
    'TaxonomyValidator',
    'RenderingValidator',
    'DirectiveValidator',
    # Phase 3 Lite
    'CacheValidator',
    'PerformanceValidator',
]

