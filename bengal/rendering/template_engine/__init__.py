"""
Template engine backward compatibility shim.

.. deprecated:: 1.0
    This module is deprecated. Use ``bengal.rendering.engines`` instead.

Migration Guide:
    Replace direct TemplateEngine imports with the factory function:

    .. code-block:: python

        # DEPRECATED (will be removed in v2.0)
        from bengal.rendering.template_engine import TemplateEngine
        engine = TemplateEngine(site)

        # RECOMMENDED
        from bengal.rendering.engines import create_engine
        engine = create_engine(site)

Rationale:
    The ``bengal.rendering.engines`` package provides a pluggable engine
    system supporting multiple template backends (Jinja2, Mako, Patitas).
    The factory function ``create_engine()`` reads the configured engine
    from ``bengal.yaml`` and returns the appropriate implementation.

This shim maintains backward compatibility by aliasing ``TemplateEngine``
to ``JinjaTemplateEngine``. It uses lazy imports to avoid circular
dependency issues during module loading.

Related Modules:
    - bengal.rendering.engines: New engine factory (use this)
    - bengal.rendering.engines.jinja: Jinja2 implementation
    - bengal.rendering.engines.protocol: Engine interface protocol
"""

from __future__ import annotations


def __getattr__(name: str):
    """Lazy import for backward compatibility with TemplateEngine alias."""
    if name == "TemplateEngine":
        from bengal.rendering.engines.jinja import JinjaTemplateEngine

        return JinjaTemplateEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["TemplateEngine"]
