"""
Template engine package for Jinja2 page rendering.

Provides template rendering, template function registration, and optional
template profiling for performance analysis. Integrates with theme system
for template discovery and asset manifest for cache-busting.

Key Concepts:
    - Template inheritance: Child themes inherit parent templates
    - Bytecode caching: Compiled templates cached for faster subsequent renders
    - Template profiling: Optional timing data collection via --profile-templates
    - Strict mode: StrictUndefined enabled for better error detection

Public API:
    - TemplateEngine: Main template engine class

Related Modules:
    - bengal.rendering.template_profiler: Profiling implementation
    - bengal.rendering.template_functions: Template function registry
    - bengal.utils.theme_registry: Theme resolution and discovery
"""

from __future__ import annotations

from bengal.rendering.template_engine.core import TemplateEngine

__all__ = ["TemplateEngine"]


