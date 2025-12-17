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
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from bengal.autodoc.utils import get_function_parameters, get_function_return_info

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.autodoc.base import DocElement
    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """Register autodoc template functions with Jinja2 environment."""
    env.filters.update(
        {
            "get_params": get_params,
            "param_count": param_count,
            "return_type": return_type,
            "get_return_info": get_return_info,
            "get_element_stats": get_element_stats,
        }
    )

    env.globals.update(
        {
            "get_params": get_params,
            "param_count": param_count,
            "return_type": return_type,
            "get_return_info": get_return_info,
            "get_element_stats": get_element_stats,
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
