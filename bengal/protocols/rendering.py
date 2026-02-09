"""
Rendering protocols for template engines and syntax highlighting.

This module defines interface contracts for rendering components:
- Template engines (Jinja2, Kida)
- Syntax highlighting backends (Rosettes)
- Role and directive handlers (Patitas integration)

Design Philosophy:
- **Protocol composition**: Large protocols split into focused interfaces
- **Runtime checkable**: Can verify implementations at runtime
- **Clear contracts**: Each method documents preconditions and guarantees
- **Thread-safe**: All implementations must be thread-safe for parallel builds

See Also:
- bengal.rendering.engines: Engine factory and registration
- bengal.rendering.highlighting: Highlighting backend factory
- bengal.parsing.backends.patitas: Patitas integration

"""

from __future__ import annotations

from collections.abc import Callable, MutableMapping
from enum import Flag, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.core import Site
    from bengal.rendering.engines.errors import TemplateError


# =============================================================================
# Template Environment Protocol
# =============================================================================


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
        - kida.Environment: Kida template engine

    """

    globals: MutableMapping[str, Any]
    filters: MutableMapping[str, Callable[..., Any]]
    tests: MutableMapping[str, Callable[..., bool]]


# =============================================================================
# Engine Capability Flags
# =============================================================================


class EngineCapability(Flag):
    """
    Capabilities that template engines may support.

    Using Flag enum allows:
    - Composable capabilities (BLOCK_CACHING | INTROSPECTION)
    - Single property on engine (vs multiple can_* methods)
    - Easy extensibility (add new capabilities without API change)
    - Type-safe capability checks

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
    CONTEXT_VALIDATION = auto()  # Can validate context before rendering
    FRAGMENT_RENDERING = auto()  # Can render individual blocks/fragments


# =============================================================================
# Template Engine Protocols (Composable)
# =============================================================================


@runtime_checkable
class TemplateRenderer(Protocol):
    """
    Core rendering capability - the minimum viable engine.

    This is the minimal interface for template rendering. Functions that
    only need to render templates should accept this protocol, not the
    full TemplateEngine.

    Thread Safety:
        Implementations MUST be thread-safe. render_template() and
        render_string() may be called concurrently from multiple
        render threads during parallel builds.

    Example:
            >>> def render_page(engine: TemplateRenderer, page: Page) -> str:
            ...     return engine.render_template("page.html", {"page": page})

    """

    site: Site
    template_dirs: list[Path]

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


@runtime_checkable
class TemplateIntrospector(Protocol):
    """
    Optional introspection capabilities for template engines.

    Provides methods for querying template existence and paths.
    Not all engines need to implement this.

    """

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


@runtime_checkable
class TemplateValidator(Protocol):
    """
    Optional validation capabilities for template engines.

    Provides syntax validation for templates. Useful for CI/CD
    and pre-commit validation.

    """

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


@runtime_checkable
class TemplateEngine(TemplateRenderer, TemplateIntrospector, TemplateValidator, Protocol):
    """
    Full template engine with all capabilities.

    This is the complete interface that combines rendering, introspection,
    and validation. Use this when you need all engine capabilities.

    For simpler use cases, prefer the focused protocols:
    - TemplateRenderer: Just rendering
    - TemplateIntrospector: Template discovery
    - TemplateValidator: Syntax validation

    Thread Safety:
        All methods MUST be thread-safe for parallel builds.

    Example:
            >>> def validate_site(engine: TemplateEngine) -> list[TemplateError]:
            ...     return engine.validate()

    """

    @property
    def capabilities(self) -> EngineCapability:
        """
        Return engine capabilities for feature detection.

        Enables capability-based feature detection instead of
        engine name string comparisons.

        Returns:
            EngineCapability flags indicating supported features
        """
        ...

    def has_capability(self, cap: EngineCapability) -> bool:
        """
        Check if engine has a specific capability.

        Args:
            cap: Capability to check for

        Returns:
            True if engine supports the capability
        """
        ...

    def precompile_templates(self, template_names: list[str] | None = None) -> int:
        """
        Optional: Pre-compile templates to warm the cache.

        Some engines support precompiling templates ahead of rendering
        to avoid compile-on-demand overhead. This is especially beneficial
        when using bytecode caching.

        Args:
            template_names: Optional list of template names to precompile.
                           If None, precompiles all templates.

        Returns:
            Number of templates compiled

        Note:
            This is an optional method. Engines that don't support it
            should not implement it. Callers should use hasattr() to check.
        """
        ...


# Backwards compatibility alias
TemplateEngineProtocol = TemplateEngine


# =============================================================================
# Syntax Highlighting Protocol
# =============================================================================


@runtime_checkable
class HighlightService(Protocol):
    """
    Unified interface for syntax highlighting.

    This protocol bridges Bengal with highlighting backends (Rosettes
    or custom implementations). Implementations handle the translation
    from this interface to backend-specific APIs.

    Thread Safety:
        Implementations MUST be thread-safe. The highlight() method
        may be called concurrently from multiple render threads.

    Example (Rosettes adapter):
            >>> class RosettesHighlightService:
            ...     def __init__(self):
            ...         self._formatter = HtmlFormatter()
            ...
            ...     @property
            ...     def name(self) -> str:
            ...         return "rosettes"
            ...
            ...     def highlight(self, code, language, hl_lines=None, linenos=False):
            ...         lexer = get_lexer(language)
            ...         config = FormatConfig(hl_lines=hl_lines, linenos=linenos)
            ...         return self._formatter.format_string(lexer.tokenize(code), config)
            ...
            ...     def supports_language(self, language):
            ...         return has_lexer(language)

    """

    @property
    def name(self) -> str:
        """
        Backend identifier (e.g., 'rosettes', 'pygments').

        Contract:
            - MUST be lowercase, hyphen-separated
            - MUST be stable (same value across calls)
        """
        ...

    def highlight(
        self,
        code: str,
        language: str,
        *,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
        **options: Any,
    ) -> str:
        """
        Render code with syntax highlighting.

        Args:
            code: Source code to highlight
            language: Programming language identifier
            hl_lines: 1-indexed line numbers to emphasize (optional)
            show_linenos: Include line numbers in output
            **options: Backend-specific options (passed through)

        Returns:
            HTML string with highlighted code

        Contract:
            - MUST return valid HTML (never raise for bad input)
            - MUST escape HTML entities in code
            - MUST use CSS classes (not inline styles)
            - SHOULD fall back to plain text for unknown languages
        """
        ...

    def supports_language(self, language: str) -> bool:
        """
        Check if backend supports the given language.

        Args:
            language: Language identifier or alias

        Returns:
            True if highlighting is available

        Contract:
            - MUST NOT raise exceptions
            - SHOULD handle common aliases (js -> javascript)
        """
        ...


# Backwards compatibility alias
HighlightBackend = HighlightService


# =============================================================================
# Role and Directive Protocols
# =============================================================================


@runtime_checkable
class RoleHandler(Protocol):
    """
    Protocol for role implementations.

    Roles are inline text processors like :doc:`reference` or :ref:`label`.
    They are the inline counterpart to block-level directives.

    Thread Safety:
        Implementations MUST be thread-safe. Roles may be processed
        concurrently during parallel page rendering.

    Example:
            >>> class DocRole:
            ...     name = "doc"
            ...
            ...     def render(self, target: str, text: str | None, context: dict) -> str:
            ...         page = context.get("site").get_page(target)
            ...         label = text or page.title
            ...         return f'<a href="{page.href}">{label}</a>'

    """

    @property
    def name(self) -> str:
        """Role name (e.g., 'doc', 'ref', 'term')."""
        ...

    def render(
        self,
        target: str,
        text: str | None,
        context: dict[str, Any],
    ) -> str:
        """
        Render the role to HTML.

        Args:
            target: Role target (the part inside backticks)
            text: Optional display text (from :role:`text <target>`)
            context: Render context with 'site', 'page', etc.

        Returns:
            HTML string

        Contract:
            - MUST return valid HTML
            - MUST escape user-provided text
            - SHOULD handle missing targets gracefully
        """
        ...


@runtime_checkable
class DirectiveHandler(Protocol):
    """
    Protocol for directive implementations.

    Directives are block-level processors like ```{note} or ```{warning}.
    They are the block counterpart to inline roles.

    Thread Safety:
        Implementations MUST be thread-safe. Directives may be processed
        concurrently during parallel page rendering.

    Example:
            >>> class NoteDirective:
            ...     name = "note"
            ...     has_content = True
            ...
            ...     def render(self, content: str, options: dict, context: dict) -> str:
            ...         return f'<div class="admonition note">{content}</div>'

    """

    @property
    def name(self) -> str:
        """Directive name (e.g., 'note', 'warning', 'code-block')."""
        ...

    @property
    def has_content(self) -> bool:
        """Whether directive accepts content body."""
        ...

    def render(
        self,
        content: str,
        options: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        """
        Render the directive to HTML.

        Args:
            content: Directive body content (may be empty)
            options: Directive options from YAML header
            context: Render context with 'site', 'page', etc.

        Returns:
            HTML string

        Contract:
            - MUST return valid HTML
            - MUST escape user-provided content
            - SHOULD validate options and provide helpful errors
        """
        ...


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "DirectiveHandler",
    # Engine capabilities
    "EngineCapability",
    "HighlightBackend",  # Backwards compatibility
    # Highlighting
    "HighlightService",
    # Roles and directives
    "RoleHandler",
    "TemplateEngine",
    "TemplateEngineProtocol",  # Backwards compatibility
    # Template environment
    "TemplateEnvironment",
    "TemplateIntrospector",
    # Template engine protocols (composable)
    "TemplateRenderer",
    "TemplateValidator",
]
