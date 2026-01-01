"""
Autodoc template functions for API documentation.

Provides normalized access to DocElement metadata across all extractor types
(Python, CLI, OpenAPI). Templates should use these functions instead of
directly accessing element.metadata.

View Dataclasses (for theme developers):
    - MemberView: Normalized Python method/function view
    - ParamView: Normalized parameter view
    - CommandView: Normalized CLI command view
    - OptionView: Normalized CLI option/argument view

Filters:
    - element | members: Get normalized Python members (methods/functions)
    - element | commands: Get normalized CLI commands
    - element | options: Get normalized CLI options/arguments

Legacy Functions:
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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bengal.autodoc.utils import get_function_parameters, get_function_return_info

if TYPE_CHECKING:
    from bengal.autodoc.base import DocElement
    from bengal.autodoc.models.cli import CLICommandMetadata, CLIOptionMetadata
    from bengal.autodoc.models.python import PythonFunctionMetadata
    from bengal.core.site import Site
    from bengal.rendering.engines.protocol import TemplateEnvironment


# =============================================================================
# View Dataclasses for Theme Developers
# =============================================================================


@dataclass(frozen=True, slots=True)
class ParamView:
    """
    Normalized parameter view for templates.

    Provides consistent access to parameter data for Python functions,
    CLI commands, and other elements with parameters.

    Attributes:
        name: Parameter name
        type: Type annotation (e.g., "str", "int | None")
        default: Default value as string (e.g., "None", "'hello'")
        required: Whether parameter is required
        description: Parameter description from docstring
        kind: Parameter kind (positional, keyword, var_positional, var_keyword)
    """

    name: str
    type: str
    default: str | None
    required: bool
    description: str
    kind: str

    @classmethod
    def from_dict(cls, param: dict[str, Any]) -> ParamView:
        """Create from normalized parameter dict."""
        return cls(
            name=param.get("name", ""),
            type=param.get("type", ""),
            default=param.get("default"),
            required=param.get("required", False),
            description=param.get("description", ""),
            kind=param.get("kind", "positional_or_keyword"),
        )


@dataclass(frozen=True, slots=True)
class MemberView:
    """
    Normalized Python member view for templates.

    Provides consistent access to method/function data regardless of
    how it's stored in the DocElement.

    Attributes:
        name: Member name
        signature: Full signature string
        description: Description/docstring
        return_type: Return type annotation
        return_description: Return value description
        params: Tuple of ParamView objects
        is_async: Whether function is async
        is_property: Whether function is a property
        is_classmethod: Whether function is a classmethod
        is_staticmethod: Whether function is a staticmethod
        is_abstract: Whether function is abstract
        is_deprecated: Whether function is deprecated
        is_private: Whether name starts with underscore
        href: Link to member page (or anchor)
        decorators: Tuple of decorator names
        typed_metadata: Full PythonFunctionMetadata (for advanced use)
    """

    name: str
    signature: str
    description: str
    return_type: str
    return_description: str
    params: tuple[ParamView, ...]
    is_async: bool
    is_property: bool
    is_classmethod: bool
    is_staticmethod: bool
    is_abstract: bool
    is_deprecated: bool
    is_private: bool
    href: str
    decorators: tuple[str, ...]
    typed_metadata: Any  # PythonFunctionMetadata or None

    @classmethod
    def from_doc_element(cls, el: DocElement) -> MemberView:
        """Create from DocElement."""
        meta: PythonFunctionMetadata | None = el.typed_metadata  # type: ignore[assignment]

        # Extract from typed_metadata or fall back to metadata dict
        if meta and hasattr(meta, "signature"):
            signature = meta.signature or ""
            return_type = meta.return_type or "None"
            is_async = meta.is_async
            is_property = meta.is_property
            is_classmethod = meta.is_classmethod
            is_staticmethod = meta.is_staticmethod
            decorators = meta.decorators or ()

            # Get return description from parsed_doc
            return_desc = ""
            if meta.parsed_doc and meta.parsed_doc.returns:
                return_desc = meta.parsed_doc.returns

            # Build params from typed_metadata.parameters
            params = tuple(
                ParamView(
                    name=p.name,
                    type=p.type_hint or "",
                    default=p.default,
                    required=p.default is None and p.kind != "var_positional",
                    description=p.description or "",
                    kind=p.kind,
                )
                for p in (meta.parameters or ())
                if p.name not in ("self", "cls")
            )
        else:
            # Fall back to metadata dict
            m = el.metadata or {}
            signature = m.get("signature", "")
            return_type = m.get("return_type") or m.get("returns") or "None"
            is_async = m.get("is_async", False)
            is_property = m.get("is_property", False)
            is_classmethod = m.get("is_classmethod", False)
            is_staticmethod = m.get("is_staticmethod", False)
            decorators = tuple(m.get("decorators", ()))
            return_desc = m.get("return_description", "")

            # Build params from get_function_parameters
            raw_params = get_function_parameters(el, exclude_self=True)
            params = tuple(ParamView.from_dict(p) for p in raw_params)

        # Check for deprecated in decorators
        is_deprecated = "deprecated" in decorators or any(
            "deprecated" in d.lower() for d in decorators
        )

        return cls(
            name=el.name,
            signature=signature,
            description=el.description,
            return_type=return_type,
            return_description=return_desc,
            params=params,
            is_async=is_async,
            is_property=is_property,
            is_classmethod=is_classmethod,
            is_staticmethod=is_staticmethod,
            is_abstract="abstractmethod" in decorators,
            is_deprecated=is_deprecated,
            is_private=el.name.startswith("_"),
            href=el.href or f"#{el.name}",
            decorators=decorators,
            typed_metadata=meta,
        )


@dataclass(frozen=True, slots=True)
class OptionView:
    """
    Normalized CLI option/argument view for templates.

    Provides consistent access to CLI option data.

    Attributes:
        name: Option name (e.g., "verbose")
        flags: Option flags as tuple (e.g., ("-v", "--verbose"))
        flags_str: Flags as comma-separated string
        type: Type name (e.g., "STRING", "INT", "BOOL")
        description: Help text
        default: Default value
        required: Whether option is required
        is_flag: Whether option is a boolean flag
        is_argument: Whether this is a positional argument (not an option)
        multiple: Whether option accepts multiple values
        envvar: Environment variable name
        typed_metadata: Full CLIOptionMetadata (for advanced use)
    """

    name: str
    flags: tuple[str, ...]
    flags_str: str
    type: str
    description: str
    default: Any
    required: bool
    is_flag: bool
    is_argument: bool
    multiple: bool
    envvar: str | None
    typed_metadata: Any  # CLIOptionMetadata or None

    @classmethod
    def from_doc_element(cls, el: DocElement) -> OptionView:
        """Create from DocElement."""
        meta: CLIOptionMetadata | None = el.typed_metadata  # type: ignore[assignment]

        if meta and hasattr(meta, "param_type"):
            flags = meta.opts or ()
            return cls(
                name=el.name,
                flags=flags,
                flags_str=", ".join(flags) if flags else el.name,
                type=meta.type_name or "STRING",
                description=meta.help_text or el.description,
                default=meta.default,
                required=meta.required,
                is_flag=meta.is_flag,
                is_argument=meta.param_type == "argument",
                multiple=meta.multiple,
                envvar=meta.envvar,
                typed_metadata=meta,
            )
        else:
            # Fall back to metadata dict
            m = el.metadata or {}
            flags = tuple(m.get("opts", ()))
            return cls(
                name=el.name,
                flags=flags,
                flags_str=", ".join(flags) if flags else el.name,
                type=m.get("type_name", "STRING"),
                description=m.get("help_text", el.description),
                default=m.get("default"),
                required=m.get("required", False),
                is_flag=m.get("is_flag", False),
                is_argument=m.get("param_type") == "argument",
                multiple=m.get("multiple", False),
                envvar=m.get("envvar"),
                typed_metadata=None,
            )


@dataclass(frozen=True, slots=True)
class CommandView:
    """
    Normalized CLI command view for templates.

    Provides consistent access to CLI command data.

    Attributes:
        name: Command name
        description: Command description/help text
        usage: Usage string (if available)
        href: Link to command page
        is_group: Whether this is a command group
        is_hidden: Whether command is hidden
        option_count: Number of options
        argument_count: Number of arguments
        subcommand_count: Number of subcommands (if group)
        typed_metadata: Full CLICommandMetadata (for advanced use)
    """

    name: str
    description: str
    usage: str
    href: str
    is_group: bool
    is_hidden: bool
    option_count: int
    argument_count: int
    subcommand_count: int
    typed_metadata: Any  # CLICommandMetadata or None

    @classmethod
    def from_doc_element(cls, el: DocElement) -> CommandView:
        """Create from DocElement."""
        meta: CLICommandMetadata | None = el.typed_metadata  # type: ignore[assignment]

        # Count children by type
        children = el.children or []
        options = [c for c in children if getattr(c, "element_type", "") == "option"]
        arguments = [c for c in children if getattr(c, "element_type", "") == "argument"]
        subcommands = [
            c for c in children if getattr(c, "element_type", "") in ("command", "command-group")
        ]

        if meta and hasattr(meta, "is_group"):
            return cls(
                name=el.name,
                description=el.description,
                usage=el.metadata.get("usage", "") if el.metadata else "",
                href=el.href or f"#{el.name}",
                is_group=meta.is_group,
                is_hidden=meta.is_hidden,
                option_count=len(options) or meta.option_count,
                argument_count=len(arguments) or meta.argument_count,
                subcommand_count=len(subcommands),
                typed_metadata=meta,
            )
        else:
            m = el.metadata or {}
            return cls(
                name=el.name,
                description=el.description,
                usage=m.get("usage", ""),
                href=el.href or f"#{el.name}",
                is_group=m.get("is_group", False),
                is_hidden=m.get("is_hidden", False),
                option_count=len(options),
                argument_count=len(arguments),
                subcommand_count=len(subcommands),
                typed_metadata=None,
            )


# =============================================================================
# Filter Functions for Theme Developers
# =============================================================================


def members_filter(element: DocElement | None) -> list[MemberView]:
    """
    Normalize Python element members for templates.

    Returns a list of MemberView objects for methods, functions, and properties.

    Usage:
        {% for m in element | members %}
          <a href="{{ m.href }}">{{ m.name }}</a>
          {% if m.is_async %}<span class="badge">async</span>{% end %}
        {% end %}

    Args:
        element: DocElement containing children (class, module)

    Returns:
        List of MemberView objects
    """
    if element is None:
        return []

    children = getattr(element, "children", None) or []
    member_types = {"method", "function", "property"}

    return [
        MemberView.from_doc_element(child)
        for child in children
        if getattr(child, "element_type", "") in member_types
    ]


def commands_filter(element: DocElement | None) -> list[CommandView]:
    """
    Normalize CLI element commands for templates.

    Returns a list of CommandView objects for commands and command groups.

    Usage:
        {% for cmd in element | commands %}
          <a href="{{ cmd.href }}">{{ cmd.name }}</a>
          <span class="badge">{{ cmd.option_count }} options</span>
        {% end %}

    Args:
        element: DocElement containing children (CLI group)

    Returns:
        List of CommandView objects
    """
    if element is None:
        return []

    children = getattr(element, "children", None) or []
    command_types = {"command", "command-group"}

    return [
        CommandView.from_doc_element(child)
        for child in children
        if getattr(child, "element_type", "") in command_types
    ]


def options_filter(element: DocElement | None) -> list[OptionView]:
    """
    Normalize CLI element options for templates.

    Returns a list of OptionView objects for options and arguments.

    Usage:
        {% for opt in element | options %}
          <code>{{ opt.flags_str }}</code>
          <span>{{ opt.description }}</span>
          {% if opt.required %}<span class="badge">required</span>{% end %}
        {% end %}

    Args:
        element: DocElement containing children (CLI command)

    Returns:
        List of OptionView objects (options first, then arguments)
    """
    if element is None:
        return []

    children = getattr(element, "children", None) or []
    option_types = {"option", "argument"}

    views = [
        OptionView.from_doc_element(child)
        for child in children
        if getattr(child, "element_type", "") in option_types
    ]

    # Sort: options first, then arguments
    return sorted(views, key=lambda v: (v.is_argument, v.name))


def member_view_filter(element: DocElement | None) -> MemberView | None:
    """
    Convert a single DocElement to a MemberView.

    Use this when iterating over a pre-filtered list of DocElements
    and you want normalized access to each member's properties.

    Usage:
        {% for el in members %}
          {% let m = el | member_view %}
          <code>{{ m.name }}</code>
          {% if m.is_async %}<span class="badge">async</span>{% end %}
        {% end %}

    Args:
        element: DocElement to convert

    Returns:
        MemberView or None if element is None
    """
    if element is None:
        return None
    return MemberView.from_doc_element(element)


def option_view_filter(element: DocElement | None) -> OptionView | None:
    """
    Convert a single DocElement to an OptionView.

    Use this when iterating over a pre-filtered list of DocElements
    and you want normalized access to each option's properties.

    Usage:
        {% for el in options %}
          {% let opt = el | option_view %}
          <code>{{ opt.flags_str }}</code>
        {% end %}

    Args:
        element: DocElement to convert

    Returns:
        OptionView or None if element is None
    """
    if element is None:
        return None
    return OptionView.from_doc_element(element)


def command_view_filter(element: DocElement | None) -> CommandView | None:
    """
    Convert a single DocElement to a CommandView.

    Use this when iterating over a pre-filtered list of DocElements
    and you want normalized access to each command's properties.

    Usage:
        {% for el in commands %}
          {% let cmd = el | command_view %}
          <a href="{{ cmd.href }}">{{ cmd.name }}</a>
        {% end %}

    Args:
        element: DocElement to convert

    Returns:
        CommandView or None if element is None
    """
    if element is None:
        return None
    return CommandView.from_doc_element(element)


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


def register(env: TemplateEnvironment, site: Site) -> None:
    """Register functions with template environment."""
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
            # View filters for theme developers (list)
            "members": members_filter,
            "commands": commands_filter,
            "options": options_filter,
            # View filters for theme developers (single element)
            "member_view": member_view_filter,
            "option_view": option_view_filter,
            "command_view": command_view_filter,
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
            # View filters for theme developers (list)
            "members": members_filter,
            "commands": commands_filter,
            "options": options_filter,
            # View filters for theme developers (single element)
            "member_view": member_view_filter,
            "option_view": option_view_filter,
            "command_view": command_view_filter,
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
