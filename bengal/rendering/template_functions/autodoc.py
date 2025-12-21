"""
Autodoc template functions for API documentation.

Provides normalized access to DocElement metadata across all extractor types
(Python, CLI, OpenAPI). Templates should use these functions instead of
directly accessing element.metadata.

Functions:
    - get_params(element): Get normalized parameters list
    - get_return_info(element): Get normalized return type info
    - param_count(element): Count of parameters (excluding self/cls)
    - return_type(element): Return type string or 'None'
    - get_element_stats(element): Get display stats for element children

Ergonomic Helpers (Tier 3 - Portable Context Globals):
    - children_by_type(children, element_type): Filter children by type
    - public_only(members): Filter to public members (no underscore prefix)
    - private_only(members): Filter to private members (underscore prefix)

These helper functions are registered as both Jinja filters and globals,
making them portable across any Python-based template engine.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from bengal.autodoc.utils import get_function_parameters, get_function_return_info

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.autodoc.base import DocElement
    from bengal.core.site import Site


def is_autodoc_page(page: Any) -> bool:
    """
    Check if a page is autodoc-generated (template helper).

    This is a template-friendly wrapper around bengal.utils.autodoc.is_autodoc_page
    that can be used in Jinja templates.

    Args:
        page: Page object to check

    Returns:
        True if page is autodoc-generated
    """
    from bengal.utils.autodoc import is_autodoc_page as _is_autodoc_page

    return _is_autodoc_page(page)


def register(env: Environment, site: Site) -> None:
    """Register autodoc template functions with Jinja2 environment."""
    env.filters.update(
        {
            "get_params": get_params,
            "param_count": param_count,
            "return_type": return_type,
            "get_return_info": get_return_info,
            "get_element_stats": get_element_stats,
            # Ergonomic helpers (Tier 3)
            "children_by_type": children_by_type,
            "public_only": public_only,
            "private_only": private_only,
            # Page detection
            "is_autodoc_page": is_autodoc_page,
        }
    )

    env.globals.update(
        {
            "get_params": get_params,
            "param_count": param_count,
            "return_type": return_type,
            "get_return_info": get_return_info,
            "get_element_stats": get_element_stats,
            # Ergonomic helpers (Tier 3) - Portable context globals
            "children_by_type": children_by_type,
            "public_only": public_only,
            "private_only": private_only,
            # Page detection
            "is_autodoc_page": is_autodoc_page,
        }
    )


def get_params(element: DocElement, exclude_self: bool = True) -> list[dict[str, Any]]:
    """
    Get normalized parameters for any DocElement with parameters.

    Returns a list of dicts with consistent keys:
        - name: Parameter name
        - type: Type annotation (or None)
        - default: Default value (or None)
        - required: Whether required
        - description: Description text

    Usage in templates:
        {% for param in element | get_params %}
          {{ param.name }}: {{ param.type }}
        {% endfor %}

    Args:
        element: DocElement (function, method, CLI command, OpenAPI endpoint)
        exclude_self: Exclude 'self' and 'cls' parameters (default True)

    Returns:
        List of normalized parameter dicts
    """
    return get_function_parameters(element, exclude_self=exclude_self)


def param_count(element: DocElement, exclude_self: bool = True) -> int:
    """
    Get count of parameters for an element.

    Usage in templates:
        {{ element | param_count }} parameters

    Args:
        element: DocElement with parameters
        exclude_self: Exclude 'self' and 'cls' (default True)

    Returns:
        Number of parameters
    """
    return len(get_function_parameters(element, exclude_self=exclude_self))


def return_type(element: DocElement) -> str:
    """
    Get return type string for an element.

    Usage in templates:
        Returns: {{ element | return_type }}

    Args:
        element: DocElement (function, method, etc.)

    Returns:
        Return type string or 'None' if not specified
    """
    info = get_function_return_info(element)
    return info.get("type") or "None"


def get_return_info(element: DocElement) -> dict[str, Any]:
    """
    Get normalized return info for an element.

    Returns a dict with:
        - type: Return type string (or None)
        - description: Return description (or None)

    Usage in templates:
        {% set ret = element | get_return_info %}
        {% if ret.type and ret.type != 'None' %}
          Returns: {{ ret.type }}
          {% if ret.description %} — {{ ret.description }}{% endif %}
        {% endif %}

    Args:
        element: DocElement (function, method, etc.)

    Returns:
        Dict with 'type' and 'description' keys
    """
    return get_function_return_info(element)


def get_element_stats(element: DocElement) -> list[dict[str, Any]]:
    """
    Extract display stats from a DocElement based on its children types.

    Counts children by element_type and returns a list of stats suitable
    for rendering in templates.

    Usage in templates:
        {% set stats = element | get_element_stats %}
        {% if stats %}
        <div class="page-hero__stats">
          {% for stat in stats %}
          <span class="page-hero__stat">
            <span class="page-hero__stat-value">{{ stat.value }}</span>
            <span class="page-hero__stat-label">{{ stat.label }}</span>
          </span>
          {% endfor %}
        </div>
        {% endif %}

    Args:
        element: DocElement with children to count

    Returns:
        List of dicts with 'value' (count) and 'label' (singular/plural name)
    """
    if not element or not hasattr(element, "children") or not element.children:
        return []

    # Count children by element_type
    type_counts = Counter(child.element_type for child in element.children)

    # Map element types to display labels (singular, plural)
    type_labels = {
        "class": ("Class", "Classes"),
        "function": ("Function", "Functions"),
        "method": ("Method", "Methods"),
        "property": ("Property", "Properties"),
        "attribute": ("Attribute", "Attributes"),
        "command": ("Command", "Commands"),
        "command-group": ("Group", "Groups"),
        "option": ("Option", "Options"),
        "argument": ("Argument", "Arguments"),
        "endpoint": ("Endpoint", "Endpoints"),
        "schema": ("Schema", "Schemas"),
        "module": ("Module", "Modules"),
        "package": ("Package", "Packages"),
    }

    stats = []
    # Preserve a consistent ordering
    for etype in type_labels:
        count = type_counts.get(etype, 0)
        if count > 0:
            singular, plural = type_labels[etype]
            stats.append(
                {
                    "value": count,
                    "label": singular if count == 1 else plural,
                }
            )

    return stats


# =========================================================================
# ERGONOMIC HELPER FUNCTIONS (Tier 3 from RFC)
#
# These functions simplify common template patterns for filtering autodoc
# elements. They are registered as both filters and globals to work with
# any Python-based template engine (portable context globals).
# =========================================================================


def children_by_type(children: list[Any], element_type: str) -> list[Any]:
    """
    Filter children by element_type.

    This replaces verbose Jinja filter chains like:
        {% set methods = children | selectattr('element_type', 'eq', 'method') | list %}

    With a simple function call:
        {% set methods = children_by_type(children, 'method') %}

    Note: This function is portable across template engines because it's
    pure Python and can be injected as a context global in any renderer.

    Args:
        children: List of child elements (DocElement or similar)
        element_type: Type to filter (method, function, class, attribute, etc.)

    Returns:
        List of children matching the type (empty list if none match)

    Example:
        {% set children = element.children or [] %}
        {% set methods = children_by_type(children, 'method') %}
        {% set functions = children_by_type(children, 'function') %}
        {% set classes = children_by_type(children, 'class') %}
        {% set attributes = children_by_type(children, 'attribute') %}
    """
    if not children:
        return []
    return [c for c in children if getattr(c, "element_type", None) == element_type]


def public_only(members: list[Any]) -> list[Any]:
    """
    Filter to members not starting with underscore.

    This replaces verbose Jinja filter chains like:
        {% set public = members | rejectattr('name', 'startswith', '_') | list %}

    With a simple function call:
        {% set public = public_only(members) %}

    Note: This function is portable across template engines because it's
    pure Python and can be injected as a context global in any renderer.

    Args:
        members: List of elements with a 'name' attribute

    Returns:
        List of members whose name does not start with underscore

    Example:
        {% set methods = children_by_type(element.children, 'method') %}
        {% set public_methods = public_only(methods) %}
    """
    if not members:
        return []
    return [m for m in members if not getattr(m, "name", "").startswith("_")]


def private_only(members: list[Any]) -> list[Any]:
    """
    Filter to members starting with underscore (internal).

    This replaces verbose Jinja filter chains like:
        {% set private = members | selectattr('name', 'startswith', '_') | list %}

    With a simple function call:
        {% set private = private_only(members) %}

    Note: This function is portable across template engines because it's
    pure Python and can be injected as a context global in any renderer.

    Args:
        members: List of elements with a 'name' attribute

    Returns:
        List of members whose name starts with underscore

    Example:
        {% set methods = children_by_type(element.children, 'method') %}
        {% set private_methods = private_only(methods) %}
    """
    if not members:
        return []
    return [m for m in members if getattr(m, "name", "").startswith("_")]
