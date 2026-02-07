"""
Rendering subsystem for Bengal SSG.

This package transforms parsed content into final HTML output through a
multi-stage pipeline: parsing, AST processing, template rendering, and
output generation.

Architecture:
The rendering subsystem follows a pipeline architecture:

1. **Parsing** - Markdown/content → HTML via configurable parser engines
2. **Transformation** - Link rewriting, TOC extraction, API doc enhancement
3. **Template Rendering** - Kida templates (default) with rich context and functions
4. **Output** - Final HTML with baseurl handling and formatting

Subpackages:
pipeline/
    Core rendering pipeline orchestrating all stages. Thread-safe with
    per-worker parser caching for parallel builds.

engines/
    Pluggable template engine system. Kida is the default (Bengal's native
    engine); Jinja2, Mako, and Patitas (template engine) are optional alternatives.

parsers/
    Markdown parser implementations (Patitas is default,
    Python-Markdown for full feature support).

plugins/
    Mistune plugins for enhanced markdown: variable substitution,
    cross-references, badges, icons, and documentation directives.

template_functions/
    30+ template functions organized by responsibility: strings,
    collections, dates, URLs, navigation, SEO, and more.

rosettes/
    Built-in syntax highlighting engine. Lock-free, 50+ languages,
    designed for Python 3.14t free-threading.

Key Classes:
- RenderingPipeline: Main pipeline class coordinating all rendering stages
- Renderer: Individual page rendering with template integration

Quick Start:
    >>> from bengal.rendering import RenderingPipeline
    >>> pipeline = RenderingPipeline(site)
    >>> pipeline.process_page(page)

Related Modules:
- bengal.orchestration.render_orchestrator: Build-level rendering coordination
- bengal.build.tracking: Incremental build support
- bengal.core.page: Page model being rendered

See Also:
- architecture/rendering.md: Rendering architecture documentation
- architecture/performance.md: Performance optimization patterns

Performance Note:
This module uses lazy imports for RenderingPipeline and Renderer to
allow lightweight subpackages (like rosettes) to be imported without
pulling in the heavy rendering infrastructure.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.rendering.pipeline import RenderingPipeline
    from bengal.rendering.renderer import Renderer

__all__ = ["Renderer", "RenderingPipeline"]


def __getattr__(name: str) -> Any:
    """Lazily resolve top-level re-exports.

    This keeps subpackage imports (like rosettes) lightweight while
    preserving the existing `bengal.rendering.RenderingPipeline` API.

    """
    if name == "RenderingPipeline":
        from bengal.rendering.pipeline import RenderingPipeline

        return RenderingPipeline
    if name == "Renderer":
        from bengal.rendering.renderer import Renderer

        return Renderer
    raise AttributeError(f"module 'bengal.rendering' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted([*globals().keys(), "RenderingPipeline", "Renderer"])
