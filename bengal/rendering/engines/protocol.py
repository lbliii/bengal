"""
Template engine protocol definition.

This module defines the interface contract that ALL template engines must implement.
The protocol ensures consistent behavior across Jinja2, Mako, Patitas, and any
custom or third-party engines.

Design Philosophy:
    - **No optional methods**: Every method is required for predictable behavior
    - **Runtime checkable**: Can verify implementations at runtime
    - **Clear contracts**: Each method documents preconditions and guarantees
    - **Error consistency**: Standardized exception types across engines

Required Attributes:
    - site: Site instance for accessing config and content
    - template_dirs: Ordered search paths for template resolution

Required Methods:
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

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.core import Site
    from bengal.rendering.engines.errors import TemplateError


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
