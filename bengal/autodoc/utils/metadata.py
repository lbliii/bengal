"""
Typed metadata access utilities for autodoc.

Provides type-safe accessor functions for DocElement.typed_metadata with automatic
fallback to the untyped metadata dict. Use these instead of direct `.metadata.get()`
calls for better IDE support and type safety.

Functions:
- Python: get_python_class_*, get_python_function_*
- CLI: get_cli_command_*, get_cli_group_*
- OpenAPI: get_openapi_*
- Normalized: get_function_parameters, get_function_return_info

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.autodoc.base import DocElement


# =============================================================================
# Python Metadata Accessors
# =============================================================================


def get_python_module_all_exports(element: DocElement) -> tuple[str, ...] | None:
    """
    Get module __all__ exports with type-safe access.

    Args:
        element: DocElement with element_type "module"

    Returns:
        Tuple of exported names if __all__ is defined, None otherwise

    """
    from bengal.autodoc.models import PythonModuleMetadata

    if isinstance(element.typed_metadata, PythonModuleMetadata):
        if not element.typed_metadata.has_all:
            return None
        return element.typed_metadata.all_exports
    if element.metadata.get("has_all"):
        exports = element.metadata.get("all_exports") or element.metadata.get("has_all")
        return tuple(exports) if isinstance(exports, (list, tuple)) else None
    return None


def get_python_class_bases(element: DocElement) -> tuple[str, ...]:
    """
    Get class base classes with type-safe access.

    Args:
        element: DocElement with element_type "class"

    Returns:
        Tuple of base class names (e.g., ("ABC", "Mixin"))

    Example:
            >>> bases = get_python_class_bases(class_element)
            >>> if "ABC" in bases:
            ...     print("Abstract class")

    """
    from bengal.autodoc.models import PythonClassMetadata

    if isinstance(element.typed_metadata, PythonClassMetadata):
        return element.typed_metadata.bases
    return tuple(element.metadata.get("bases", []))


def get_python_class_decorators(element: DocElement) -> tuple[str, ...]:
    """
    Get class decorators with type-safe access.

    Args:
        element: DocElement with element_type "class"

    Returns:
        Tuple of decorator names (e.g., ("dataclass", "frozen"))

    """
    from bengal.autodoc.models import PythonClassMetadata

    if isinstance(element.typed_metadata, PythonClassMetadata):
        return element.typed_metadata.decorators
    return tuple(element.metadata.get("decorators", []))


def get_python_class_is_dataclass(element: DocElement) -> bool:
    """
    Check if class is a dataclass with type-safe access.

    Args:
        element: DocElement with element_type "class"

    Returns:
        True if class has @dataclass decorator

    """
    from bengal.autodoc.models import PythonClassMetadata

    if isinstance(element.typed_metadata, PythonClassMetadata):
        return element.typed_metadata.is_dataclass
    return element.metadata.get("is_dataclass", False)


def get_python_function_decorators(element: DocElement) -> tuple[str, ...]:
    """
    Get function/method decorators with type-safe access.

    Args:
        element: DocElement with element_type "function" or "method"

    Returns:
        Tuple of decorator names (e.g., ("classmethod", "override"))

    """
    from bengal.autodoc.models import PythonFunctionMetadata

    if isinstance(element.typed_metadata, PythonFunctionMetadata):
        return element.typed_metadata.decorators
    return tuple(element.metadata.get("decorators", []))


def get_python_function_is_property(element: DocElement) -> bool:
    """
    Check if function is a property with type-safe access.

    Args:
        element: DocElement with element_type "function" or "method"

    Returns:
        True if function has @property decorator

    """
    from bengal.autodoc.models import PythonFunctionMetadata

    if isinstance(element.typed_metadata, PythonFunctionMetadata):
        return element.typed_metadata.is_property
    return element.metadata.get("is_property", False)


def get_python_function_signature(element: DocElement) -> str:
    """
    Get function signature with type-safe access.

    Args:
        element: DocElement with element_type "function" or "method"

    Returns:
        Signature string (e.g., "def build(force: bool = False) -> None")

    """
    from bengal.autodoc.models import PythonFunctionMetadata

    if isinstance(element.typed_metadata, PythonFunctionMetadata):
        return element.typed_metadata.signature
    return element.metadata.get("signature", "")


def get_python_function_return_type(element: DocElement) -> str | None:
    """
    Get function return type with type-safe access.

    Args:
        element: DocElement with element_type "function" or "method"

    Returns:
        Return type string or None

    """
    from bengal.autodoc.models import PythonFunctionMetadata

    if isinstance(element.typed_metadata, PythonFunctionMetadata):
        return element.typed_metadata.return_type
    return element.metadata.get("returns")


# =============================================================================
# CLI Metadata Accessors
# =============================================================================


def get_cli_command_callback(element: DocElement) -> str | None:
    """
    Get CLI command callback name with type-safe access.

    Args:
        element: DocElement with element_type "command"

    Returns:
        Callback function name or None

    """
    from bengal.autodoc.models import CLICommandMetadata

    if isinstance(element.typed_metadata, CLICommandMetadata):
        return element.typed_metadata.callback
    return element.metadata.get("callback")


def get_cli_command_option_count(element: DocElement) -> int:
    """
    Get CLI command option count with type-safe access.

    Args:
        element: DocElement with element_type "command"

    Returns:
        Number of options

    """
    from bengal.autodoc.models import CLICommandMetadata

    if isinstance(element.typed_metadata, CLICommandMetadata):
        return element.typed_metadata.option_count
    return element.metadata.get("option_count", 0)


def get_cli_group_command_count(element: DocElement) -> int:
    """
    Get CLI group command count with type-safe access.

    Args:
        element: DocElement with element_type "command-group"

    Returns:
        Number of subcommands

    """
    from bengal.autodoc.models import CLIGroupMetadata

    if isinstance(element.typed_metadata, CLIGroupMetadata):
        return element.typed_metadata.command_count
    return element.metadata.get("command_count", 0)


# =============================================================================
# OpenAPI Metadata Accessors
# =============================================================================


def get_openapi_tags(element: DocElement) -> tuple[str, ...]:
    """
    Get OpenAPI endpoint tags with type-safe access.

    Args:
        element: DocElement with element_type "openapi_endpoint"

    Returns:
        Tuple of tag names (e.g., ("users", "admin"))

    """
    from bengal.autodoc.models import OpenAPIEndpointMetadata

    if isinstance(element.typed_metadata, OpenAPIEndpointMetadata):
        return element.typed_metadata.tags
    return tuple(element.metadata.get("tags", []))


def get_openapi_method(element: DocElement) -> str:
    """
    Get OpenAPI HTTP method with type-safe access.

    Args:
        element: DocElement with element_type "openapi_endpoint"

    Returns:
        HTTP method string (e.g., "GET", "POST")

    """
    from bengal.autodoc.models import OpenAPIEndpointMetadata

    if isinstance(element.typed_metadata, OpenAPIEndpointMetadata):
        return element.typed_metadata.method
    return element.metadata.get("method", "").upper()


def get_openapi_path(element: DocElement) -> str:
    """
    Get OpenAPI endpoint path with type-safe access.

    Args:
        element: DocElement with element_type "openapi_endpoint"

    Returns:
        Path string (e.g., "/users/{id}")

    """
    from bengal.autodoc.models import OpenAPIEndpointMetadata

    if isinstance(element.typed_metadata, OpenAPIEndpointMetadata):
        return element.typed_metadata.path
    return element.metadata.get("path", "")


def get_openapi_operation_id(element: DocElement) -> str | None:
    """
    Get OpenAPI operation ID with type-safe access.

    Args:
        element: DocElement with element_type "openapi_endpoint"

    Returns:
        Operation ID string or None

    """
    from bengal.autodoc.models import OpenAPIEndpointMetadata

    if isinstance(element.typed_metadata, OpenAPIEndpointMetadata):
        return element.typed_metadata.operation_id
    return element.metadata.get("operation_id")


# =============================================================================
# Normalized Parameter Access
# =============================================================================
#
# Functions that provide a unified parameter format across all extractors.
# This is the canonical way to access parameters in templates.


def get_function_parameters(
    element: DocElement,
    exclude_self: bool = True,
) -> list[dict[str, Any]]:
    """
    Get normalized function/method parameters across all extractor types.

    This is the canonical way to access parameters in templates. It handles:
    - Python functions/methods (typed_metadata.parameters or metadata.args)
    - CLI options (typed_metadata or metadata.options)
    - OpenAPI endpoints (typed_metadata.parameters or metadata.parameters)

    Each parameter is normalized to a consistent dict format:
        {
            "name": str,           # Parameter name
            "type": str | None,    # Type annotation/schema type
            "default": str | None, # Default value
            "required": bool,      # Whether required (derived from default)
            "description": str,    # Description from docstring
        }

    Args:
        element: DocElement to extract parameters from
        exclude_self: If True, excludes 'self' and 'cls' parameters (default True)

    Returns:
        List of normalized parameter dicts (empty list if element has no params)

    Example:
            >>> params = get_function_parameters(method_element)
            >>> for p in params:
            ...     print(f"{p['name']}: {p['type']} = {p['default']}")

    """
    # Guard: Only process elements that can have parameters
    valid_types = {"function", "method", "command", "openapi_endpoint", "endpoint"}
    if hasattr(element, "element_type") and element.element_type not in valid_types:
        return []

    from bengal.autodoc.models import (
        CLICommandMetadata,
        OpenAPIEndpointMetadata,
        PythonFunctionMetadata,
    )

    params: list[dict[str, Any]] = []

    # Python functions/methods
    if isinstance(element.typed_metadata, PythonFunctionMetadata):
        for p in element.typed_metadata.parameters:
            if exclude_self and p.name in ("self", "cls"):
                continue
            params.append(
                {
                    "name": p.name,
                    "type": p.type_hint,
                    "default": p.default,
                    "required": p.default is None
                    and p.kind not in ("var_positional", "var_keyword"),
                    "description": p.description or "",
                }
            )
        return params

    # OpenAPI endpoints
    if isinstance(element.typed_metadata, OpenAPIEndpointMetadata):
        params.extend(
            {
                "name": p.name,
                "type": p.schema_type,
                "default": None,
                "required": p.required,
                "description": p.description or "",
            }
            for p in element.typed_metadata.parameters
        )
        return params

    # CLI commands - get options from children
    if isinstance(element.typed_metadata, CLICommandMetadata):
        from bengal.autodoc.models import CLIOptionMetadata

        for child in element.children:
            if isinstance(child.typed_metadata, CLIOptionMetadata):
                opt = child.typed_metadata
                # Format default value
                default_str = None
                if opt.default is not None and not opt.is_flag:
                    default_str = str(opt.default)

                params.append(
                    {
                        "name": opt.name,
                        "type": opt.type_name,
                        "default": default_str,
                        "required": opt.required,
                        "description": opt.help_text or "",
                    }
                )
        return params

    # Fallback to legacy metadata dict
    # Try 'args' first (Python extractor), then 'parameters' (others)
    legacy_params = element.metadata.get("args") or element.metadata.get("parameters") or []

    for p in legacy_params:
        if isinstance(p, dict):
            name = p.get("name", "")
            if exclude_self and name in ("self", "cls"):
                continue
            params.append(
                {
                    "name": name,
                    "type": p.get("type_hint") or p.get("type") or p.get("schema_type"),
                    "default": p.get("default"),
                    "required": p.get("required", p.get("default") is None),
                    "description": p.get("description")
                    or p.get("docstring")
                    or p.get("help_text")
                    or "",
                }
            )
        elif isinstance(p, str):
            # Simple string param (just the name)
            if exclude_self and p in ("self", "cls"):
                continue
            params.append(
                {
                    "name": p,
                    "type": None,
                    "default": None,
                    "required": True,
                    "description": "",
                }
            )

    return params


def get_function_return_info(element: DocElement) -> dict[str, Any]:
    """
    Get normalized return type information across all extractor types.

    Returns a consistent dict format:
        {
            "type": str | None,        # Return type annotation
            "description": str | None, # Return description from docstring
        }

    Args:
        element: DocElement to extract return info from

    Returns:
        Dict with 'type' and 'description' keys (both None if not applicable)

    Example:
            >>> ret = get_function_return_info(func_element)
            >>> if ret['type'] and ret['type'] != 'None':
            ...     print(f"Returns: {ret['type']}")

    """
    # Guard: Only process elements that can have return types
    valid_types = {"function", "method", "openapi_endpoint", "endpoint"}
    if hasattr(element, "element_type") and element.element_type not in valid_types:
        return {"type": None, "description": None}

    from bengal.autodoc.models import (
        OpenAPIEndpointMetadata,
        PythonFunctionMetadata,
    )

    # Python functions/methods
    if isinstance(element.typed_metadata, PythonFunctionMetadata):
        return_desc = None
        if element.typed_metadata.parsed_doc:
            return_desc = element.typed_metadata.parsed_doc.returns
        return {
            "type": element.typed_metadata.return_type,
            "description": return_desc,
        }

    # OpenAPI endpoints - return info from responses
    if isinstance(element.typed_metadata, OpenAPIEndpointMetadata):
        # Find the success response (200, 201, etc.)
        for resp in element.typed_metadata.responses:
            if resp.status_code.startswith("2"):
                return {
                    "type": resp.schema_ref or resp.content_type,
                    "description": resp.description,
                }
        return {"type": None, "description": None}

    # Fallback to legacy metadata dict
    returns = element.metadata.get("returns")
    if isinstance(returns, dict):
        return {
            "type": returns.get("type"),
            "description": returns.get("description"),
        }
    elif isinstance(returns, str):
        return {
            "type": returns,
            "description": None,
        }

    return {"type": None, "description": None}
