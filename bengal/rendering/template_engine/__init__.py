"""
Template engine package - backward compatibility re-exports.

DEPRECATED: Use bengal.rendering.engines instead.

    # NEW (recommended)
    from bengal.rendering.engines import create_engine
    engine = create_engine(site)

    # OLD (deprecated)
    from bengal.rendering.template_engine import TemplateEngine
    engine = TemplateEngine(site)
"""

from __future__ import annotations


def __getattr__(name: str):
    """Lazy import to avoid circular import issues."""
    if name == "TemplateEngine":
        from bengal.rendering.engines.jinja import JinjaTemplateEngine

        return JinjaTemplateEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["TemplateEngine"]
