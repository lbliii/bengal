"""
Rendering subsystem for Bengal SSG.

This package transforms parsed content into final HTML output through a
multi-stage pipeline: parsing, AST processing, template rendering, and
output generation.

Architecture:
    The rendering subsystem follows a pipeline architecture:

    1. **Parsing** - Markdown/content → HTML via configurable parser engines
    2. **Transformation** - Link rewriting, TOC extraction, API doc enhancement
    3. **Template Rendering** - Jinja2 templates with rich context and functions
    4. **Output** - Final HTML with baseurl handling and formatting

Subpackages:
    pipeline/
        Core rendering pipeline orchestrating all stages. Thread-safe with
        per-worker parser caching for parallel builds.

    engines/
        Pluggable template engine system. Jinja2 is the default; Mako and
        Patitas are optional alternatives.

    parsers/
        Markdown parser implementations (Mistune recommended for speed,
        Python-Markdown for full feature support).

    plugins/
        Mistune plugins for enhanced markdown: variable substitution,
        cross-references, badges, icons, and documentation directives.

    template_functions/
        30+ template functions organized by responsibility: strings,
        collections, dates, URLs, navigation, SEO, and more.

Key Classes:
    - RenderingPipeline: Main pipeline class coordinating all rendering stages
    - Renderer: Individual page rendering with template integration

Quick Start:
    >>> from bengal.rendering import RenderingPipeline
    >>> pipeline = RenderingPipeline(site, dependency_tracker=tracker)
    >>> pipeline.process_page(page)

Related Modules:
    - bengal.orchestration.render_orchestrator: Build-level rendering coordination
    - bengal.cache.dependency_tracker: Incremental build support
    - bengal.core.page: Page model being rendered

See Also:
    - architecture/rendering.md: Rendering architecture documentation
    - architecture/performance.md: Performance optimization patterns
"""

from __future__ import annotations

from bengal.rendering.pipeline import RenderingPipeline
from bengal.rendering.renderer import Renderer

__all__ = ["Renderer", "RenderingPipeline"]
