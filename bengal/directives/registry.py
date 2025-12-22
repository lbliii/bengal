"""Lazy-loading directive registry for on-demand directive imports.

This module provides a registry that loads directive classes only when
requested, maintaining fast import times while supporting the full
directive library. Each directive module is imported on first use,
reducing cold start time for CLI operations that don't need directives.

Public API:
    - ``get_directive(name)``: Lazy-load a directive class by name.
    - ``register_all()``: Pre-load all directives (for testing/inspection).
    - ``get_known_directive_names()``: Get all registered directive names.
    - ``get_directive_classes()``: Get all unique directive classes.
    - ``KNOWN_DIRECTIVE_NAMES``: Frozenset of registered directive names.
    - ``DIRECTIVE_CLASSES``: List of all directive classes (lazy-loaded).

Internal Architecture:
    - ``_DIRECTIVE_MAP``: Maps directive names to module paths.
    - ``_loaded_directives``: Cache of already-loaded directive classes.

Example:
    Get a specific directive class::

        from bengal.directives.registry import get_directive

        DropdownDirective = get_directive("dropdown")
        if DropdownDirective:
            directive = DropdownDirective()

    Pre-load all directives for inspection::

        from bengal.directives.registry import register_all, DIRECTIVE_CLASSES

        register_all()
        print(f"Loaded {len(DIRECTIVE_CLASSES)} directive classes")

See Also:
    - ``bengal.directives.base``: ``BengalDirective`` base class.
    - ``bengal.directives.factory``: Plugin factory using this registry.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.directives.base import BengalDirective

logger = get_logger(__name__)

# =============================================================================
# DIRECTIVE MAP - Maps directive names to module paths
# =============================================================================
# Each entry maps a directive name to the module containing its implementation.
# The module must expose the directive class via the class's DIRECTIVE_NAMES.

_DIRECTIVE_MAP: dict[str, str] = {
    # Admonitions (note, tip, warning, danger, error, info, example, success, etc.)
    "note": "bengal.directives.admonitions",
    "tip": "bengal.directives.admonitions",
    "warning": "bengal.directives.admonitions",
    "danger": "bengal.directives.admonitions",
    "error": "bengal.directives.admonitions",
    "info": "bengal.directives.admonitions",
    "example": "bengal.directives.admonitions",
    "success": "bengal.directives.admonitions",
    "caution": "bengal.directives.admonitions",
    "seealso": "bengal.directives.admonitions",
    # Badges
    "badge": "bengal.directives.badge",
    "bdg": "bengal.directives.badge",
    # Build badge
    "build": "bengal.directives.build",
    # Buttons
    "button": "bengal.directives.button",
    # Cards
    "cards": "bengal.directives.cards",
    "card": "bengal.directives.cards",
    "child-cards": "bengal.directives.cards",
    "grid": "bengal.directives.cards",
    "grid-item-card": "bengal.directives.cards",
    # Tabs
    "tab-set": "bengal.directives.tabs",
    "tabs": "bengal.directives.tabs",  # Alias for tab-set
    "tab-item": "bengal.directives.tabs",
    "tab": "bengal.directives.tabs",  # Alias for tab-item
    # Dropdowns
    "dropdown": "bengal.directives.dropdown",
    "details": "bengal.directives.dropdown",
    # Code tabs
    "code-tabs": "bengal.directives.code_tabs",
    "code_tabs": "bengal.directives.code_tabs",
    # Tables
    "list-table": "bengal.directives.list_table",
    "data-table": "bengal.directives.data_table",
    # Glossary
    "glossary": "bengal.directives.glossary",
    # Icons
    "icon": "bengal.directives.icon",
    "svg-icon": "bengal.directives.icon",
    # Checklist
    "checklist": "bengal.directives.checklist",
    # Container
    "container": "bengal.directives.container",
    "div": "bengal.directives.container",
    # Steps
    "steps": "bengal.directives.steps",
    "step": "bengal.directives.steps",
    # Rubric
    "rubric": "bengal.directives.rubric",
    # Target
    "target": "bengal.directives.target",
    "anchor": "bengal.directives.target",
    # Example label
    "example-label": "bengal.directives.example_label",
    # Includes
    "include": "bengal.directives.include",
    "literalinclude": "bengal.directives.literalinclude",
    # Navigation
    "breadcrumbs": "bengal.directives.navigation",
    "siblings": "bengal.directives.navigation",
    "prev-next": "bengal.directives.navigation",
    "related": "bengal.directives.navigation",
    # Marimo
    "marimo": "bengal.directives.marimo",
    # Video embeds
    "youtube": "bengal.directives.video",
    "vimeo": "bengal.directives.video",
    "video": "bengal.directives.video",
    # Developer tool embeds
    "gist": "bengal.directives.embed",
    "codepen": "bengal.directives.embed",
    "codesandbox": "bengal.directives.embed",
    "stackblitz": "bengal.directives.embed",
    # Terminal recording embeds
    "asciinema": "bengal.directives.terminal",
    # Figure and audio
    "figure": "bengal.directives.figure",
    "audio": "bengal.directives.figure",
    # Gallery
    "gallery": "bengal.directives.gallery",
    # Version-aware directives
    "since": "bengal.directives.versioning",
    "versionadded": "bengal.directives.versioning",
    "deprecated": "bengal.directives.versioning",
    "versionremoved": "bengal.directives.versioning",
    "changed": "bengal.directives.versioning",
    "versionchanged": "bengal.directives.versioning",
}

# Cache of loaded directive classes
_loaded_directives: dict[str, type[BengalDirective]] = {}

# =============================================================================
# PUBLIC API
# =============================================================================


def get_directive(name: str) -> type[BengalDirective] | None:
    """Get a directive class by name, loading it lazily if needed.

    Looks up the directive in the registry and imports its module on first
    access. Results are cached for subsequent calls.

    Args:
        name: Directive name (e.g., ``"dropdown"``, ``"tab-set"``).

    Returns:
        The directive class if found, ``None`` if not registered or import fails.

    Example:
        >>> DropdownDirective = get_directive("dropdown")
        >>> if DropdownDirective:
        ...     directive = DropdownDirective()
    """
    if name in _loaded_directives:
        return _loaded_directives[name]

    module_path = _DIRECTIVE_MAP.get(name)
    if not module_path:
        logger.debug("directive_not_found", directive=name)
        return None

    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        logger.warning(
            "directive_import_error",
            directive=name,
            module=module_path,
            error=str(e),
        )
        return None

    # Find the directive class that handles this name
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and hasattr(attr, "DIRECTIVE_NAMES")
            and name in getattr(attr, "DIRECTIVE_NAMES", [])
        ):
            _loaded_directives[name] = attr
            return attr

    logger.warning(
        "directive_class_not_found",
        directive=name,
        module=module_path,
    )
    return None


def register_all() -> None:
    """Pre-load all registered directives into the cache.

    Imports all directive modules and populates ``_loaded_directives``.
    Useful for testing, inspection, or ensuring all directives are
    available before processing content in a batch.
    """
    for name in _DIRECTIVE_MAP:
        get_directive(name)


def get_known_directive_names() -> frozenset[str]:
    """Return all registered directive names as a frozenset.

    This includes all directive names and their aliases (e.g., both
    ``"dropdown"`` and ``"details"`` for the dropdown directive).

    Returns:
        Frozenset of all directive names in the registry.
    """
    return frozenset(_DIRECTIVE_MAP.keys())


# Cached for performance - computed once at import time
KNOWN_DIRECTIVE_NAMES: frozenset[str] = get_known_directive_names()


def get_directive_classes() -> list[type]:
    """Return all unique directive classes.

    Triggers ``register_all()`` to ensure all modules are imported, then
    returns deduplicated directive classes (since multiple names may map
    to the same class, e.g., ``"dropdown"`` and ``"details"``).

    Returns:
        List of unique directive class types.
    """
    register_all()
    # Deduplicate - multiple names may map to the same class
    return list(set(_loaded_directives.values()))


# Lazy property for DIRECTIVE_CLASSES
_directive_classes: list[type] | None = None


def _get_directive_classes() -> list[type]:
    """Return directive classes, loading and caching on first access.

    Internal function backing the ``DIRECTIVE_CLASSES`` module attribute.

    Returns:
        List of all unique directive classes.
    """
    global _directive_classes
    if _directive_classes is None:
        _directive_classes = get_directive_classes()
    return _directive_classes


# Provide as module-level for compatibility
DIRECTIVE_CLASSES: list[type] = []  # Populated on first access via __getattr__


def __getattr__(name: str) -> list[type]:
    """Provide lazy access to ``DIRECTIVE_CLASSES`` via PEP 562.

    Implements module-level ``__getattr__`` to defer loading all directive
    classes until ``DIRECTIVE_CLASSES`` is actually accessed.

    Args:
        name: The attribute name being accessed.

    Returns:
        For ``DIRECTIVE_CLASSES``, returns the list of all directive classes.

    Raises:
        AttributeError: If the requested attribute does not exist.
    """
    if name == "DIRECTIVE_CLASSES":
        return _get_directive_classes()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
