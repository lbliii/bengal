"""
Template function registry for Bengal SSG.

This module provides 30+ template functions for use in Jinja2 templates,
organized into focused modules by responsibility.

Each module self-registers its functions to avoid god objects and maintain
clean separation of concerns.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jinja2 import Environment
    from bengal.core.site import Site

from . import (
    strings,
    collections,
    math_functions,
    dates,
    urls,
    content,
    data,
    advanced_strings,
    files,
    advanced_collections,
    images,
    seo,
    debug,
    taxonomies,
    pagination_helpers,
    crossref,
)


def register_all(env: 'Environment', site: 'Site') -> None:
    """
    Register all template functions with Jinja2 environment.
    
    This is a thin coordinator - each module handles its own registration
    following the Single Responsibility Principle.
    
    Args:
        env: Jinja2 environment to register functions with
        site: Site instance for context-aware functions
    """
    # Phase 1: Essential functions (30 functions)
    strings.register(env, site)
    collections.register(env, site)
    math_functions.register(env, site)
    dates.register(env, site)
    urls.register(env, site)
    
    # Phase 2: Advanced functions (25 functions)
    content.register(env, site)
    data.register(env, site)
    advanced_strings.register(env, site)
    files.register(env, site)
    advanced_collections.register(env, site)
    
    # Phase 3: Specialized functions (20 functions)
    images.register(env, site)
    seo.register(env, site)
    debug.register(env, site)
    taxonomies.register(env, site)
    pagination_helpers.register(env, site)
    
    # Phase 4: Cross-reference functions (5 functions)
    crossref.register(env, site)


__all__ = [
    'register_all',
    'strings',
    'collections',
    'math_functions',
    'dates',
    'urls',
    'content',
    'data',
    'advanced_strings',
    'files',
    'advanced_collections',
    'images',
    'seo',
    'debug',
    'taxonomies',
    'pagination_helpers',
    'crossref',
]

