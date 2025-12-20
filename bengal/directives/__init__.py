"""
Directive system for Bengal templates.

Implements lazy-loading to prevent performance regression when extracting
directives from the rendering package.

This package provides:
    - Lazy-loading registry for directive classes
    - Base directive class with contract validation
    - All standard Bengal directives (admonitions, tabs, cards, etc.)

Architecture:
    Directives are loaded lazily via `get_directive()` to avoid importing
    all directive implementations at package import time. This maintains
    fast startup times while allowing the full directive library to be
    available on demand.

Usage:
    from bengal.directives import get_directive, register_all

    # Get a specific directive (lazy-loaded)
    DropdownDirective = get_directive("dropdown")

    # Pre-load all directives (for testing/inspection)
    register_all()

Related:
    - bengal/rendering/plugins/directives/: Original directive location (deprecated)
    - plan/ready/plan-architecture-refactoring.md: Migration plan
"""

from __future__ import annotations

from bengal.directives.registry import (
    DIRECTIVE_CLASSES,
    KNOWN_DIRECTIVE_NAMES,
    get_directive,
    get_known_directive_names,
    register_all,
)

__all__ = [
    "DIRECTIVE_CLASSES",
    "KNOWN_DIRECTIVE_NAMES",
    "get_directive",
    "get_known_directive_names",
    "register_all",
]
