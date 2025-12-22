"""
Utility functions for the autodoc documentation extraction system.

This module provides shared utilities used across all extractors and
the orchestration layer.

Text Processing:
    - `sanitize_text()`: Cleans docstrings for markdown generation
    - `truncate_text()`: Safely truncates long descriptions
    - `_convert_sphinx_roles()`: Converts RST cross-references to markdown

Grouping & Path Resolution:
    - `auto_detect_prefix_map()`: Scans packages for automatic grouping
    - `apply_grouping()`: Maps module paths to documentation groups
    - `resolve_cli_url_path()`: Converts CLI command names to URL paths

Typed Metadata Access:
    Type-safe accessor functions for DocElement.typed_metadata with automatic
    fallback to the untyped metadata dict. Use these instead of direct
    `.metadata.get()` calls for better IDE support:

    - `get_python_class_bases()`, `get_python_class_decorators()`
    - `get_python_function_signature()`, `get_python_function_return_type()`
    - `get_cli_command_callback()`, `get_cli_group_command_count()`
    - `get_openapi_method()`, `get_openapi_path()`, `get_openapi_tags()`

Normalized Parameter Access:
    - `get_function_parameters()`: Unified parameter format across extractors
    - `get_function_return_info()`: Unified return type information

Example:
    >>> from bengal.autodoc.utils import sanitize_text, get_function_parameters
    >>> clean = sanitize_text("    Indented docstring text.\\n\\n    More here.")
    >>> params = get_function_parameters(doc_element)

Related:
    - bengal/autodoc/base.py: DocElement data model
    - bengal/autodoc/models/: Typed metadata dataclasses
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.autodoc.base import DocElement


def _convert_sphinx_roles(text: str) -> str:
    """
    Convert reStructuredText-style cross-reference roles to inline code.

    Handles common reStructuredText roles:
    - :class:`ClassName` or :class:`~module.ClassName` → `ClassName`
    - :func:`function_name` → `function_name()`
    - :meth:`method_name` → `method_name()`
    - :mod:`module_name` → `module_name`
    - :attr:`attribute_name` → `attribute_name`
    - :exc:`ExceptionName` → `ExceptionName`

    Args:
        text: Text containing reStructuredText roles

    Returns:
        Text with roles converted to inline code

    Example:
        >>> _convert_sphinx_roles("Use :class:`~bengal.core.Site` class")
        'Use `Site` class'
    """
    # Pattern: :role:`~module.path.ClassName` or :role:`ClassName`
    # The ~ prefix means "show only the last component"
    # Add leading space to prevent running into previous word (markdown collapses multiple spaces)

    # :class:`~module.ClassName` → `ClassName`
    # :class:`ClassName` → `ClassName`
    text = re.sub(r":class:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1`", text)

    # :func:`function_name` → `function_name()`
    text = re.sub(r":func:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1()`", text)

    # :meth:`method_name` → `method_name()`
    text = re.sub(r":meth:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1()`", text)

    # :mod:`module.name` → `module.name` (keep full module path)
    text = re.sub(r":mod:`~?([a-zA-Z0-9_.]+)`", r" `\1`", text)

    # :attr:`attribute_name` → `attribute_name`
    text = re.sub(r":attr:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1`", text)

    # :exc:`ExceptionName` → `ExceptionName`
    text = re.sub(r":exc:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1`", text)

    # :const:`CONSTANT_NAME` → `CONSTANT_NAME`
    text = re.sub(r":const:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1`", text)

    # :data:`variable_name` → `variable_name`
    text = re.sub(r":data:`~?(?:[a-zA-Z0-9_.]+\.)?([a-zA-Z0-9_]+)`", r" `\1`", text)

    return text


def sanitize_text(text: str | None) -> str:
    """
    Clean user-provided text for markdown generation.

    This function is the single source of truth for text cleaning across
    all autodoc extractors. It prevents common markdown rendering issues by:

    - Removing leading/trailing whitespace
    - Dedenting indented blocks (prevents accidental code blocks)
    - Normalizing line endings
    - Collapsing excessive blank lines

    Args:
        text: Raw text from docstrings, help text, or API specs

    Returns:
        Cleaned text safe for markdown generation

    Example:
        >>> text = '''
        ...     Indented docstring text.
        ...
        ...     More content here.
        ... '''
        >>> sanitize_text(text)
        'Indented docstring text.\\n\\nMore content here.'
    """
    if not text:
        return ""

    # Dedent to remove common leading whitespace
    # This prevents "    text" from becoming a code block in markdown
    text = textwrap.dedent(text)

    # Strip leading/trailing whitespace
    text = text.strip()

    # Normalize line endings (Windows → Unix)
    text = text.replace("\r\n", "\n")

    # Convert reStructuredText-style cross-references to inline code
    # :class:`ClassName` or :class:`~module.ClassName` → `ClassName`
    # :func:`function_name` → `function_name()`
    # :meth:`method_name` → `method_name()`
    # :mod:`module_name` → `module_name`
    text = _convert_sphinx_roles(text)

    # Collapse multiple blank lines to maximum of 2
    # (2 blank lines = paragraph break in markdown, more is excessive)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length, adding suffix if truncated.

    Args:
        text: Text to truncate
        max_length: Maximum length (default: 200)
        suffix: Suffix to add if truncated (default: '...')

    Returns:
        Truncated text

    Example:
        >>> truncate_text('A very long description here', max_length=20)
        'A very long descr...'
    """
    if len(text) <= max_length:
        return text

    # Find last space before max_length to avoid breaking words
    truncate_at = text.rfind(" ", 0, max_length - len(suffix))
    if truncate_at == -1:
        truncate_at = max_length - len(suffix)

    return text[:truncate_at].rstrip() + suffix


def auto_detect_prefix_map(source_dirs: list[Path], strip_prefix: str = "") -> dict[str, str]:
    """
    Auto-detect grouping from __init__.py hierarchy.

    Scans source directories for packages (directories containing __init__.py)
    and builds a prefix map for every package path. Each entry maps the full
    dotted module path to its slash-separated path relative to the stripped
    prefix (e.g., "cli.templates" → "cli/templates"). Using the full path
    ensures nested packages stay under their parent directories (cli/templates
    lives under cli/).

    Args:
        source_dirs: Directories to scan for packages
        strip_prefix: Optional dotted prefix to remove from detected modules

    Returns:
        Prefix map: {"package.path": "group_path"}

    Example:
        >>> auto_detect_prefix_map([Path("bengal")], "bengal.")
        {
            "cli": "cli",
            "cli.templates": "cli/templates",
            "core": "core",
            "cache": "cache",
        }
    """
    prefix_map: dict[str, str] = {}
    normalized_strip = strip_prefix.rstrip(".") if strip_prefix else ""
    strip_with_dot = f"{normalized_strip}." if normalized_strip else ""

    for source_dir in source_dirs:
        # Ensure source_dir is a Path
        if not isinstance(source_dir, Path):
            source_dir = Path(source_dir)

        # Skip if directory doesn't exist
        if not source_dir.exists() or not source_dir.is_dir():
            continue

        # Find all __init__.py files
        for init_file in source_dir.rglob("__init__.py"):
            package_dir = init_file.parent

            # Skip if outside source_dir (shouldn't happen with rglob)
            try:
                rel_path = package_dir.relative_to(source_dir)
            except ValueError:
                # Not relative to source_dir, skip
                continue

            # Build module name from path
            module_parts = list(rel_path.parts)
            if not module_parts:
                # Root __init__.py, skip
                continue

            module_name = ".".join(module_parts)

            # Strip prefix if configured, respecting dot boundaries
            if normalized_strip:
                if module_name == normalized_strip:
                    continue
                if strip_with_dot and module_name.startswith(strip_with_dot):
                    module_name = module_name[len(strip_with_dot) :]
                elif strip_prefix and module_name.startswith(strip_prefix):
                    # Handles cases where strip_prefix includes additional segments
                    module_name = module_name[len(strip_prefix) :].lstrip(".")

            module_name = module_name.lstrip(".")

            # Skip if empty after stripping
            if not module_name:
                continue

            display_path = module_name.replace(".", "/")
            prefix_map.setdefault(module_name, display_path)

    return prefix_map


def apply_grouping(qualified_name: str, config: dict[str, Any]) -> tuple[str | None, str]:
    """
    Apply grouping config to qualified module name.

    Args:
        qualified_name: Full module name (e.g., "bengal.cli.templates.blog")
        config: Grouping config dict with mode and prefix_map

    Returns:
        Tuple of (group_name, remaining_path):
        - group_name: Top-level group (or None if no grouping)
        - remaining_path: Path after group prefix

    Example:
        >>> apply_grouping("bengal.cli.templates.blog", {
        ...     "mode": "auto",
        ...     "prefix_map": {"cli.templates": "templates"}
        ... })
        ("templates", "blog")
    """
    mode = config.get("mode", "off")

    # Mode "off" - no grouping
    if mode == "off":
        return None, qualified_name

    # Get prefix map (already built for auto mode, provided for explicit)
    prefix_map = config.get("prefix_map", {})
    if not prefix_map:
        return None, qualified_name

    # Find longest matching prefix
    # Check for exact match first (package is the group itself)
    if qualified_name in prefix_map:
        return prefix_map[qualified_name], ""

    # Find longest matching parent prefix
    best_match = None
    best_length = 0

    for prefix in prefix_map:
        # Check if qualified_name starts with this prefix (dot-separated)
        # Only match parent packages (not exact matches, handled above)
        if qualified_name.startswith(prefix + "."):
            prefix_length = len(prefix)
            if prefix_length > best_length:
                best_match = prefix
                best_length = prefix_length

    if not best_match:
        return None, qualified_name

    # Extract group and remaining path
    group_name = prefix_map[best_match]
    remaining = qualified_name[len(best_match) :].lstrip(".")

    return group_name, remaining


def resolve_cli_url_path(qualified_name: str) -> str:
    """
    Resolve CLI qualified name to a URL path by dropping the root command.

    This ensures that CLI documentation paths are concise and don't redundantly
    include the tool name (e.g., /cli/build instead of /cli/bengal/build).

    Args:
        qualified_name: Dotted qualified name from Click/Typer (e.g. 'bengal.build')

    Returns:
        Slash-separated path relative to CLI prefix

    Example:
        >>> resolve_cli_url_path("bengal.build")
        'build'
        >>> resolve_cli_url_path("bengal.site.new")
        'site/new'
        >>> resolve_cli_url_path("bengal")
        ''
    """
    if not qualified_name:
        return ""

    parts = qualified_name.split(".")
    if len(parts) > 1:
        # Drop the first part (the root CLI name, e.g. "bengal")
        return "/".join(parts[1:])

    # This is the root group itself
    return ""


# =============================================================================
# Typed Metadata Access Helpers
# =============================================================================
#
# These functions provide type-safe access to DocElement.typed_metadata with
# automatic fallback to the untyped metadata dict. Use these instead of
# direct .metadata.get() calls for better IDE support and type safety.


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
        for p in element.typed_metadata.parameters:
            params.append(
                {
                    "name": p.name,
                    "type": p.schema_type,
                    "default": None,
                    "required": p.required,
                    "description": p.description or "",
                }
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
