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

# Re-export from new engines package for backward compatibility
from bengal.rendering.engines import create_engine
from bengal.rendering.engines.jinja import JinjaTemplateEngine

# Legacy alias: TemplateEngine points to JinjaTemplateEngine
TemplateEngine = JinjaTemplateEngine

__all__ = [
    "TemplateEngine",  # Legacy alias
    "JinjaTemplateEngine",  # Explicit Jinja2 engine
    "create_engine",  # Factory function
]
