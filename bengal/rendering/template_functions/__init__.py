"""
Template function registry for Bengal SSG.

This package provides 80+ template functions and filters organized into focused
modules by responsibility. Functions are automatically registered with the
template engine during site initialization.

Engine-Agnostic:
    These functions work with any template engine that provides a globals/filters
    interface (Jinja2, Kida, or custom engines via the adapter layer).

Architecture:
    Each submodule self-registers its functions via a ``register(env, site)``
    function, following the Single Responsibility Principle. The main
    ``register_all()`` function coordinates registration in dependency order.

Function Categories:
    Phase 1 - Essential (30 functions):
        - strings: Text manipulation (truncate, slugify, titlecase, etc.)
        - collections: List/dict operations (sort_by, group_by, filter, etc.)
        - math_functions: Numeric operations (add, multiply, round, etc.)
        - dates: Date formatting and manipulation
        - urls: URL construction and manipulation
        - get_page: Page lookup by path

    Phase 2 - Advanced (25 functions):
        - content: Content processing (markdown, highlight, excerpt)
        - data: Data file loading (yaml, json, csv)
        - advanced_strings: Regex, pluralization, translations
        - files: File operations (read, glob, exists)
        - advanced_collections: Chunking, pagination, tree operations

    Phase 3 - Specialized (20 functions):
        - images: Image processing and optimization
        - icons: Icon libraries (FontAwesome, Material, etc.)
        - seo: Meta tags, Open Graph, structured data
        - debug: Development helpers (dump, inspect, type)
        - taxonomies: Tag and category operations
        - pagination_helpers: Pagination rendering
        - i18n: Internationalization support

    Phase 4 - Cross-References (5 functions):
        - crossref: Internal linking between pages

    Phase 5 - Navigation:
        - navigation/: Breadcrumbs, TOC, auto-nav, tree building

    Phase 6 - Theme:
        - theme: Asset URLs, theme configuration access

    Phase 7 - Autodoc:
        - autodoc: API documentation helpers

    Phase 8 - Tests:
        - template_tests: Template test functions (match, draft, featured)

    Phase 9 - Versioning:
        - version_url: Smart version switching URLs

Usage in Templates:
    Functions are available directly in templates:

    .. code-block:: jinja

        {{ page.content | markdown | safe }}
        {{ pages | sort_by('date', reverse=True) }}
        {{ site.pages | where('draft', false) }}
        {% set data = load_data('data/config.yaml') %}

Registration:
    Called automatically by the template engine:

    >>> from bengal.rendering.template_functions import register_all
    >>> register_all(env, site)

Related Modules:
    - bengal.rendering.engines: Template engines that use these functions
    - bengal.rendering.template_tests: Template test registrations
    - bengal.rendering.template_context: Context wrappers for templates
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.rendering.engines.protocol import TemplateEnvironment

from bengal.rendering import template_tests

from . import (
    advanced_collections,
    advanced_strings,
    autodoc,
    collections,
    content,
    crossref,
    data,
    dates,
    debug,
    files,
    get_page,
    i18n,
    icons,
    images,
    math_functions,
    navigation,
    openapi,
    pagination_helpers,
    resources,
    seo,
    sharing,
    strings,
    taxonomies,
    theme,
    urls,
    version_url,
)

logger = get_logger(__name__)


def register_all(env: TemplateEnvironment, site: Site, engine_type: str | None = None) -> None:
    """
    Register all template functions with template environment.

    This is a thin coordinator - each module handles its own registration
    following the Single Responsibility Principle.

    Non-context-dependent functions are registered directly by their modules.
    Context-dependent functions (t, current_lang, tag_url, asset_url) are
    registered by the adapter layer (see bengal.rendering.adapters).

    Args:
        env: Template environment to register functions with
        site: Site instance for context-aware functions
        engine_type: Engine type for adapter selection (auto-detected if None).
                     If provided, also registers context-dependent functions.
    """
    logger.debug("registering_template_functions", phase="template_setup")

    # Phase 1: Essential functions (30 functions)
    strings.register(env, site)
    collections.register(env, site)
    math_functions.register(env, site)
    dates.register(env, site)
    urls.register(env, site)
    get_page.register(env, site)

    # Phase 2: Advanced functions (25 functions)
    content.register(env, site)
    data.register(env, site)
    advanced_strings.register(env, site)
    files.register(env, site)
    advanced_collections.register(env, site)

    # Phase 3: Specialized functions (20+ functions)
    images.register(env, site)
    resources.register(env, site)  # Hugo-style resources.get/match
    icons.register(env, site)
    seo.register(env, site)
    debug.register(env, site)
    taxonomies.register(env, site)
    pagination_helpers.register(env, site)
    i18n.register(env, site)
    sharing.register(env, site)

    # Phase 4: Cross-reference functions (5 functions)
    crossref.register(env, site)

    # Phase 5: Navigation functions
    navigation.register(env, site)

    # Phase 6: Theme functions
    theme.register(env, site)

    # Phase 7: Autodoc functions (normalized parameter access)
    autodoc.register(env, site)

    # Phase 7b: OpenAPI-specific functions (code samples, path highlighting)
    openapi.register(env, site)

    # Phase 8: Template tests (match, draft, featured, etc.)
    template_tests.register(env, site)

    # Phase 9: Version URL functions (smart fallback for version switching)
    version_url.register(env, site)

    # Phase 10: Context-dependent functions via adapter (if engine_type specified)
    # When engine_type is provided, register context functions automatically.
    # Otherwise, caller is responsible for calling adapters.register_context_functions()
    if engine_type is not None:
        from bengal.rendering.adapters import register_context_functions

        register_context_functions(env, site, engine_type)

    logger.debug("template_functions_registered", count=20)


__all__ = [
    "advanced_collections",
    "advanced_strings",
    "autodoc",
    "collections",
    "content",
    "crossref",
    "data",
    "dates",
    "debug",
    "files",
    "get_page",
    "icons",
    "images",
    "math_functions",
    "navigation",
    "openapi",
    "pagination_helpers",
    "register_all",
    "resources",
    "seo",
    "sharing",
    "strings",
    "taxonomies",
    "template_tests",
    "theme",
    "urls",
    "version_url",
]
