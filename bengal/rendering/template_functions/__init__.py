"""
Template function registry for Bengal SSG.

This module provides 30+ template functions for use in Jinja2 templates,
organized into focused modules by responsibility.

Each module self-registers its functions to avoid god objects and maintain
clean separation of concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site

from bengal.rendering import template_tests

from . import (
    advanced_collections,
    advanced_strings,
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
    pagination_helpers,
    seo,
    strings,
    taxonomies,
    theme,
    urls,
)

logger = get_logger(__name__)


def register_all(env: Environment, site: Site) -> None:
    """
    Register all template functions with Jinja2 environment.

    This is a thin coordinator - each module handles its own registration
    following the Single Responsibility Principle.

    Args:
        env: Jinja2 environment to register functions with
        site: Site instance for context-aware functions
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

    # Phase 3: Specialized functions (20 functions)
    images.register(env, site)
    icons.register(env, site)
    seo.register(env, site)
    debug.register(env, site)
    taxonomies.register(env, site)
    pagination_helpers.register(env, site)
    i18n.register(env, site)

    # Phase 4: Cross-reference functions (5 functions)
    crossref.register(env, site)

    # Phase 5: Navigation functions
    navigation.register(env, site)

    # Phase 6: Theme functions
    theme.register(env, site)

    # Phase 7: Template tests (match, draft, featured, etc.)
    template_tests.register(env, site)

    logger.debug("template_functions_registered", count=19)


__all__ = [
    "advanced_collections",
    "advanced_strings",
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
    "pagination_helpers",
    "register_all",
    "seo",
    "strings",
    "taxonomies",
    "template_tests",
    "theme",
    "urls",
]
