"""
Template function utilities for Jinja2 templates.

Provides utility functions accessible in templates for common operations
like related posts computation. Functions are registered with the template
engine and available globally in templates.

Key Concepts:
    - Template functions: Utility functions accessible in templates
    - Related posts: On-demand computation of related content
    - Lazy computation: Functions compute values only when needed

Related Modules:
    - bengal.rendering.template_functions: Template function modules
    - bengal.rendering.template_engine: Template engine registration
    - bengal.orchestration.related_posts: Related posts computation logic

See Also:
    - bengal/rendering/template_functions/__init__.py: Template function modules
    - bengal/rendering/template_engine/core.py: Template function registration
"""

from __future__ import annotations

from bengal.orchestration.related_posts import compute_related


def related_posts(page, limit=3):
    """On-demand compute for template context."""
    if not hasattr(page, "related_posts") or not page.related_posts:
        page.related_posts = compute_related(page, limit=limit)
    return page.related_posts[:limit]
