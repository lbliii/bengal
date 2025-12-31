"""
Template engine protocol definitions.

This module defines interface contracts for template engines and environments.
The protocols ensure consistent behavior across Jinja2, Kida, and any custom
or third-party engines.

Protocols:
    - TemplateEnvironment: Interface for environment objects (globals, filters, tests)
    - TemplateEngineProtocol: Full engine interface for rendering templates

Design Philosophy:
    - **No optional methods**: Every method is required for predictable behavior
    - **Runtime checkable**: Can verify implementations at runtime
    - **Clear contracts**: Each method documents preconditions and guarantees
    - **Error consistency**: Standardized exception types across engines

Required Attributes (TemplateEngineProtocol):
    - site: Site instance for accessing config and content
    - template_dirs: Ordered search paths for template resolution

Required Methods (TemplateEngineProtocol):
    - render_template(): Render named template file
    - render_string(): Render inline template string
    - template_exists(): Check template availability
    - get_template_path(): Resolve template to filesystem path
    - list_templates(): Enumerate available templates
    - validate(): Syntax-check all templates

Implementing Custom Engines:
    To create a custom engine, implement all protocol methods:

    .. code-block:: python

        class MyEngine:
            def __init__(self, site: Site):
                self.site = site
                self.template_dirs = [site.root_path / "templates"]

            def render_template(self, name: str, context: dict) -> str:
                # Implementation...

            # ... implement all other methods ...

    Then register it:

    >>> from bengal.rendering.engines import register_engine
    >>> register_engine("myengine", MyEngine)

Related Modules:
    - bengal.rendering.engines: Engine factory and registration
    - bengal.rendering.engines.jinja: Reference Jinja2 implementation
    - bengal.rendering.engines.errors: Exception types
"""

from __future__ import annotations

from collections.abc import Callable, MutableMapping
from enum import Flag, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.core import Site
    from bengal.rendering.engines.errors import TemplateError


@runtime_checkable
class TemplateEnvironment(Protocol):
    """
    Protocol for template environment objects.

    Template environments provide the runtime context for template rendering,
    including global variables, filters, and tests. Both Jinja2's Environment
    and Kida's Environment implement this interface.

    This protocol defines the minimal interface needed for registering
    template functions. Environments may provide additional features
    beyond this protocol.

    Attributes:
        globals: Dict-like mapping of global variables available in all templates
        filters: Dict-like mapping of filter functions (value transformers)
        tests: Dict-like mapping of test functions (boolean predicates)

    Example:
        >>> def register(env: TemplateEnvironment, site: Site) -> None:
        ...     env.globals["my_func"] = my_function
        ...     env.filters["my_filter"] = my_filter

    Implementations:
        - jinja2.Environment: Jinja2's native environment
        - bengal.rendering.kida.Environment: Kida template engine
    """

    globals: MutableMapping[str, Any]
    filters: MutableMapping[str, Callable[..., Any]]
    tests: MutableMapping[str, Callable[..., bool]]


class EngineCapability(Flag):
    """
    Capabilities that template engines may support.

    Using Flag enum allows:
    - Composable capabilities (BLOCK_CACHING | INTROSPECTION)
    - Single property on engine (vs multiple can_* methods)
    - Easy extensibility (add new capabilities without API change)
    - Type-safe capability checks

    Alternative considered: Individual `can_cache_blocks()`, `can_introspect()`
    methods. Rejected because:
    - Requires protocol changes for each new capability
    - More verbose engine implementations
    - Harder to query "what can this engine do?"

    Example:
        >>> if engine.has_capability(EngineCapability.BLOCK_CACHING):
        ...     enable_block_cache()
        >>> if EngineCapability.INTROSPECTION in engine.capabilities:
        ...     analyze_template_structure()
    """

    NONE = 0
    BLOCK_CACHING = auto()  # Can cache rendered blocks
    BLOCK_LEVEL_DETECTION = auto()  # Can detect block-level changes
    INTROSPECTION = auto()  # Can analyze template structure
    PIPELINE_OPERATORS = auto()  # Supports |> operator
    PATTERN_MATCHING = auto()  # Supports match/case in templates


@runtime_checkable
class TemplateEngineProtocol(Protocol):
    """
    Standardized interface for all Bengal template engines.

    REQUIRED ATTRIBUTES:
        site: Site instance (injected at construction)
        template_dirs: Ordered list of template search directories

    REQUIRED METHODS:
        render_template(): Render a named template
        render_string(): Render an inline template string
        template_exists(): Check if a template exists
        get_template_path(): Resolve template to filesystem path
        list_templates(): List all available templates
        validate(): Validate all templates for syntax errors

    ALL methods are required. No optional methods. This ensures:
        - Consistent behavior across engines
        - Easy testing and mocking
        - Clear contract for third-party engines
    """

    # --- Required Attributes ---

    site: Site
    template_dirs: list[Path]

    # --- Required Methods ---

    def render_template(
        self,
        name: str,
        context: dict[str, Any],
    ) -> str:
        """
        Render a named template with the given context.

        Args:
            name: Template identifier (e.g., "blog/single.html")
            context: Variables available to the template

        Returns:
            Rendered HTML string

        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateRenderError: If rendering fails

        Contract:
            - MUST automatically inject `site` and `config` into context
            - MUST search template_dirs in order (first match wins)
            - MUST raise TemplateNotFoundError (not return empty string)
        """
        ...

    def render_string(
        self,
        template: str,
        context: dict[str, Any],
    ) -> str:
        """
        Render a template string with the given context.

        Args:
            template: Template content as string
            context: Variables available to the template

        Returns:
            Rendered HTML string

        Contract:
            - MUST automatically inject `site` and `config` into context
            - MUST NOT cache the compiled template
        """
        ...

    def template_exists(self, name: str) -> bool:
        """
        Check if a template exists.

        Args:
            name: Template identifier

        Returns:
            True if template can be loaded, False otherwise

        Contract:
            - MUST NOT raise exceptions (return False instead)
            - MUST check all template_dirs
        """
        ...

    def get_template_path(self, name: str) -> Path | None:
        """
        Resolve a template name to its filesystem path.

        Args:
            name: Template identifier

        Returns:
            Absolute path to template file, or None if not found

        Contract:
            - MUST return None (not raise) if not found
            - MUST return the path that would be used by render_template()
        """
        ...

    def list_templates(self) -> list[str]:
        """
        List all available template names.

        Returns:
            Sorted list of template names (relative to template_dirs)

        Contract:
            - MUST return unique names (no duplicates)
            - MUST return sorted list
            - MUST include templates from all template_dirs
        """
        ...

    def validate(self, patterns: list[str] | None = None) -> list[TemplateError]:
        """
        Validate all templates for syntax errors.

        Args:
            patterns: Optional glob patterns to filter (e.g., ["*.html"])
                      If None, validates all templates.

        Returns:
            List of TemplateError for any invalid templates.
            Empty list if all templates are valid.

        Contract:
            - MUST NOT raise exceptions (return errors in list)
            - MUST validate syntax only (not runtime errors)
        """
        ...

    @property
    def capabilities(self) -> EngineCapability:
        """
        Return engine capabilities for feature detection.

        Enables capability-based feature detection instead of
        engine name string comparisons.

        Returns:
            EngineCapability flags indicating supported features

        Example:
            >>> if EngineCapability.BLOCK_CACHING in engine.capabilities:
            ...     enable_block_cache()
        """
        ...

    def has_capability(self, cap: EngineCapability) -> bool:
        """
        Check if engine has a specific capability.

        Convenience method for single capability checks.

        Args:
            cap: Capability to check for

        Returns:
            True if engine supports the capability

        Example:
            >>> if engine.has_capability(EngineCapability.INTROSPECTION):
            ...     metadata = engine.get_template_introspection(name)
        """
        ...
