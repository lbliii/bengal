"""Core Environment class for Kida template system.

Central configuration and template management.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bengal.rendering.kida.environment.filters import DEFAULT_FILTERS
from bengal.rendering.kida.environment.protocols import Loader
from bengal.rendering.kida.environment.registry import FilterRegistry
from bengal.rendering.kida.environment.tests import DEFAULT_TESTS
from bengal.rendering.kida.lexer import Lexer, LexerConfig
from bengal.rendering.kida.template import Template

if TYPE_CHECKING:
    pass


@dataclass
class Environment:
    """Central configuration and template management.

    Attributes:
        loader: Template loader (filesystem, dict, etc.)
        autoescape: Auto-escape HTML (default: True for .html/.xml)
        auto_reload: Check template modification times (default: True)
        optimized: Enable compiler optimizations (default: True)
        strict_none: Fail early on None comparisons during sorting (default: False)

    Thread-Safety:
        - Immutable configuration after construction
        - Copy-on-write for filters/tests
        - Lock-free template cache reads
    """

    # Configuration
    loader: Loader | None = None
    autoescape: bool | Callable[[str | None], bool] = True
    auto_reload: bool = True
    optimized: bool = True
    strict_none: bool = False  # When True, sorting with None values raises detailed errors

    # Lexer settings
    block_start: str = "{%"
    block_end: str = "%}"
    variable_start: str = "{{"
    variable_end: str = "}}"
    comment_start: str = "{#"
    comment_end: str = "#}"
    trim_blocks: bool = False
    lstrip_blocks: bool = False

    # Globals (available in all templates)
    # Includes Python builtins commonly used in templates
    globals: dict[str, Any] = field(
        default_factory=lambda: {
            "range": range,
            "dict": dict,
            "list": list,
            "set": set,
            "tuple": tuple,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "abs": abs,
            "min": min,
            "max": max,
            "sum": sum,
            "sorted": sorted,
            "reversed": reversed,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
        }
    )

    # Filters and tests (copy-on-write)
    _filters: dict[str, Callable] = field(default_factory=lambda: DEFAULT_FILTERS.copy())
    _tests: dict[str, Callable] = field(default_factory=lambda: DEFAULT_TESTS.copy())

    # Template cache (thread-safe)
    _cache: dict[str, Template] = field(default_factory=dict)
    _cache_lock: threading.RLock = field(default_factory=threading.RLock)

    def __post_init__(self) -> None:
        """Initialize derived configuration."""
        self._lexer_config = LexerConfig(
            block_start=self.block_start,
            block_end=self.block_end,
            variable_start=self.variable_start,
            variable_end=self.variable_end,
            comment_start=self.comment_start,
            comment_end=self.comment_end,
            trim_blocks=self.trim_blocks,
            lstrip_blocks=self.lstrip_blocks,
        )

    @property
    def filters(self) -> FilterRegistry:
        """Get filters (Jinja2-compatible interface)."""
        return FilterRegistry(self, "_filters")

    @property
    def tests(self) -> FilterRegistry:
        """Get tests (Jinja2-compatible interface)."""
        return FilterRegistry(self, "_tests")

    def add_filter(self, name: str, func: Callable) -> None:
        """Add a filter (copy-on-write).

        Args:
            name: Filter name (used in templates as {{ x | name }})
            func: Filter function
        """
        new_filters = self._filters.copy()
        new_filters[name] = func
        self._filters = new_filters

    def add_test(self, name: str, func: Callable) -> None:
        """Add a test (copy-on-write).

        Args:
            name: Test name (used in templates as {% if x is name %})
            func: Test function returning bool
        """
        new_tests = self._tests.copy()
        new_tests[name] = func
        self._tests = new_tests

    def get_template(self, name: str) -> Template:
        """Load and cache a template by name.

        Args:
            name: Template identifier (e.g., "index.html")

        Returns:
            Compiled Template object

        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateSyntaxError: If template has syntax errors
        """
        if self.loader is None:
            raise RuntimeError("No loader configured")

        # Check cache (lock-free read)
        cached = self._cache.get(name)
        if cached is not None and not self.auto_reload:
            return cached

        # Load and compile
        source, filename = self.loader.get_source(name)
        template = self._compile(source, name, filename)

        # Update cache (atomic swap)
        with self._cache_lock:
            new_cache = self._cache.copy()
            new_cache[name] = template
            self._cache = new_cache

        return template

    def from_string(self, source: str, name: str | None = None) -> Template:
        """Compile a template from a string.

        Args:
            source: Template source code
            name: Optional template name for error messages

        Returns:
            Compiled Template object

        Note:
            String templates are NOT cached. Use get_template() for caching.
        """
        return self._compile(source, name, None)

    def _compile(
        self,
        source: str,
        name: str | None,
        filename: str | None,
    ) -> Template:
        """Compile template source to Template object."""
        from bengal.rendering.kida.compiler import Compiler
        from bengal.rendering.kida.parser import Parser

        # Tokenize
        lexer = Lexer(source, self._lexer_config)
        tokens = list(lexer.tokenize())

        # Determine autoescape setting for this template
        should_escape = self.autoescape(name) if callable(self.autoescape) else self.autoescape

        # Parse (pass source for rich error messages)
        parser = Parser(tokens, name, filename, source, autoescape=should_escape)
        ast = parser.parse()

        # Compile
        compiler = Compiler(self)
        code = compiler.compile(ast, name, filename)

        return Template(self, code, name, filename)

    def render(self, template_name: str, *args: Any, **kwargs: Any) -> str:
        """Render a template by name with context.

        Convenience method combining get_template() and render().

        Args:
            template_name: Template identifier (e.g., "index.html")
            *args: Single dict of context variables (optional)
            **kwargs: Context variables as keyword arguments

        Returns:
            Rendered template as string

        Example:
            >>> env.render("email.html", user=user, items=items)
            '...'
        """
        return self.get_template(template_name).render(*args, **kwargs)

    def render_string(self, source: str, *args: Any, **kwargs: Any) -> str:
        """Compile and render a template string.

        Convenience method combining from_string() and render().

        Args:
            source: Template source code
            *args: Single dict of context variables (optional)
            **kwargs: Context variables as keyword arguments

        Returns:
            Rendered template as string

        Example:
            >>> env.render_string("Hello, {{ name }}!", name="World")
            'Hello, World!'
        """
        return self.from_string(source).render(*args, **kwargs)

    def filter(self, name: str | None = None) -> Callable:
        """Decorator to register a filter function.

        Args:
            name: Filter name (defaults to function name)

        Returns:
            Decorator function

        Example:
            >>> @env.filter()
            ... def double(value):
            ...     return value * 2

            >>> @env.filter("twice")
            ... def my_double(value):
            ...     return value * 2
        """

        def decorator(func: Callable) -> Callable:
            filter_name = name if name is not None else func.__name__
            self.add_filter(filter_name, func)
            return func

        return decorator

    def test(self, name: str | None = None) -> Callable:
        """Decorator to register a test function.

        Args:
            name: Test name (defaults to function name)

        Returns:
            Decorator function

        Example:
            >>> @env.test()
            ... def is_prime(value):
            ...     return value > 1 and all(value % i for i in range(2, value))
        """

        def decorator(func: Callable) -> Callable:
            test_name = name if name is not None else func.__name__
            self.add_test(test_name, func)
            return func

        return decorator

    def select_autoescape(self, name: str | None) -> bool:
        """Determine if autoescape should be enabled for a template.

        Args:
            name: Template name (may be None for string templates)

        Returns:
            True if autoescape should be enabled
        """
        if callable(self.autoescape):
            return self.autoescape(name)
        return self.autoescape
