"""
Pluggable template engine system for Bengal SSG.

This package provides a unified interface for template engines, allowing
sites to choose their preferred templating solution while maintaining
consistent behavior.

Architecture:
All template engine access MUST go through create_engine(). Direct
imports of engine classes are for type hints and testing only.

Available Engines:
kida (Default):
    Bengal's native template engine. Jinja2-compatible with unified
    block endings, pattern matching, pipeline operators, and automatic
    block caching. Supports free-threaded Python.

jinja2 (Optional):
    Industry-standard template engine. Feature-rich with excellent
    documentation and tooling support.

mako (Optional):
    Python-like syntax with full Python expression support. Install
    with: pip install bengal[mako]

patitas (Optional):
    Pure Python templates for maximum flexibility. Install with:
    pip install bengal[patitas]

Public API:
- create_engine(): Factory function (required for engine creation)
- register_engine(): Register custom/third-party engines
- TemplateEngineProtocol: Interface for custom implementations
- TemplateError: Base exception for template errors
- TemplateNotFoundError: Template file not found
- TemplateRenderError: Template rendering failed

Configuration:
Set the engine in bengal.yaml:

.. code-block:: yaml

    site:
      template_engine: kida  # default (Bengal's native engine), or jinja2, mako, patitas

Usage:
    >>> from bengal.rendering.engines import create_engine
    >>>
    >>> engine = create_engine(site)
    >>> html = engine.render("page.html", {"page": page, "site": site})

Custom Engines:
To add a third-party engine, implement TemplateEngineProtocol and register:

    >>> from bengal.rendering.engines import register_engine
    >>> register_engine("myengine", MyTemplateEngine)

Related Modules:
- bengal.rendering.template_functions: Functions available in templates
- bengal.rendering.template_context: Context wrappers for URL handling
- bengal.rendering.errors: Rich error objects for debugging

See Also:
- bengal.protocols: Canonical protocol definitions (TemplateEngine, TemplateRenderer, etc.)
- bengal.rendering.engines.jinja: Jinja2 implementation details

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.errors import BengalConfigError, ErrorCode
from bengal.rendering.engines.errors import (
    TemplateError,
    TemplateNotFoundError,
)
# Import from canonical location (bengal.protocols)
from bengal.protocols import TemplateEngine as TemplateEngineProtocol
from bengal.rendering.errors import TemplateRenderError

if TYPE_CHECKING:
    from bengal.core import Site

# Third-party engine registry (for plugins)
_ENGINES: dict[str, type[TemplateEngineProtocol]] = {}


def register_engine(name: str, engine_class: type[TemplateEngineProtocol]) -> None:
    """
    Register a third-party template engine.
    
    Args:
        name: Engine identifier (used in bengal.yaml)
        engine_class: Class implementing TemplateEngineProtocol
        
    """
    _ENGINES[name] = engine_class


def create_engine(
    site: Site,
    *,
    profile: bool = False,
) -> TemplateEngineProtocol:
    """
    Create a template engine based on site configuration.
    
    This is the ONLY way to get a template engine instance.
    
    Args:
        site: Site instance
        profile: Enable template profiling
    
    Returns:
        Engine implementing TemplateEngineProtocol
    
    Raises:
        ValueError: If engine is unknown or required package not installed
    
    Configuration:
        template_engine: kida  # default (Bengal's native engine), or "jinja2", "mako", "patitas", etc.
        
    """
    engine_name = site.config.get("template_engine", "kida")

    if engine_name == "jinja2":
        from bengal.rendering.engines.jinja import JinjaTemplateEngine

        return JinjaTemplateEngine(site, profile=profile)

    if engine_name == "kida":
        from bengal.rendering.engines.kida import KidaTemplateEngine

        return KidaTemplateEngine(site, profile=profile)

    if engine_name == "mako":
        try:
            from bengal.rendering.engines.mako import MakoTemplateEngine  # type: ignore[import-not-found]
        except ImportError as e:
            raise BengalConfigError(
                "Mako engine requires mako package. Install with: pip install bengal[mako]",
                code=ErrorCode.C003,
                suggestion="Install the mako package or use a different template engine (jinja2, patitas)",
                original_error=e,
            ) from e
        return MakoTemplateEngine(site)

    if engine_name == "patitas":
        try:
            from bengal.rendering.engines.patitas import PatitasTemplateEngine  # type: ignore[import-not-found]
        except ImportError as e:
            raise BengalConfigError(
                "Patitas engine requires patitas package. Install with: pip install bengal[patitas]",
                code=ErrorCode.C003,
                suggestion="Install the patitas package or use a different template engine (jinja2, mako)",
                original_error=e,
            ) from e
        return PatitasTemplateEngine(site)

    if engine_name in _ENGINES:
        return _ENGINES[engine_name](site)

    available = ["jinja2", "kida", "mako", "patitas", *_ENGINES.keys()]
    raise BengalConfigError(
        f"Unknown template engine: '{engine_name}'. Available: {', '.join(sorted(available))}",
        code=ErrorCode.C003,
        suggestion=f"Set template_engine to one of: {', '.join(sorted(available))}",
    )


# Public API
__all__ = [
    # Protocol
    "TemplateEngineProtocol",
    # Factory
    "create_engine",
    "register_engine",
    # Errors
    "TemplateError",
    "TemplateNotFoundError",
    "TemplateRenderError",
]
