"""
Template engine package for Jinja2 page rendering.

MIGRATION NOTE:
    This package provides backward compatibility with the legacy API.
    New code should use bengal.rendering.engines instead:

        # NEW (recommended)
        from bengal.rendering.engines import create_engine
        engine = create_engine(site)

        # LEGACY (deprecated)
        from bengal.rendering.template_engine import TemplateEngine
        engine = TemplateEngine(site)

Public API:
    - TemplateEngine: Legacy alias for JinjaTemplateEngine
    - create_engine: Factory function (preferred)

Related Modules:
    - bengal.rendering.engines: New pluggable engine system
    - bengal.rendering.template_profiler: Profiling implementation
    - bengal.rendering.template_functions: Template function registry
"""

from __future__ import annotations

# Import from legacy core.py to avoid circular import
# (engines/jinja.py imports from template_engine submodules)
from bengal.rendering.template_engine.core import TemplateEngine

__all__ = [
    "TemplateEngine",
]
