"""Core Environment class for Kida template system.

The Environment is the central hub for template configuration, compilation,
and caching. It manages loaders, filters, tests, and global variables.

Thread-Safety:
    - Immutable configuration after construction
    - Copy-on-write for filters/tests/globals (no locking)
    - LRU caches use atomic pointer swaps
    - Safe for concurrent `get_template()` and `render()` calls

Example:
    >>> from bengal.rendering.kida import Environment, FileSystemLoader
    >>> env = Environment(
    ...     loader=FileSystemLoader("templates/"),
    ...     autoescape=True,
    ...     strict=True,
    ... )
    >>> env.get_template("page.html").render(page=page)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bengal.rendering.kida.environment.filters import DEFAULT_FILTERS
from bengal.rendering.kida.environment.protocols import Loader
from bengal.rendering.kida.environment.registry import FilterRegistry
from bengal.rendering.kida.environment.tests import DEFAULT_TESTS
from bengal.rendering.kida.lexer import Lexer, LexerConfig
from bengal.rendering.kida.template import Template
from bengal.utils.lru_cache import LRUCache

if TYPE_CHECKING:
    from bengal.rendering.kida.bytecode_cache import BytecodeCache


# Default cache limits
DEFAULT_TEMPLATE_CACHE_SIZE = 400  # Max compiled templates to keep
DEFAULT_FRAGMENT_CACHE_SIZE = 1000  # Max fragment cache entries
DEFAULT_FRAGMENT_TTL = 300.0  # Fragment TTL in seconds (5 minutes)


@dataclass
class Environment:
    """Central configuration and template management hub.

    The Environment holds all template engine settings and provides the primary
    API for loading and rendering templates. It manages three key concerns:

    1. **Template Loading**: Via configurable loaders (filesystem, dict, etc.)
    2. **Compilation Settings**: Autoescape, optimizations, strict mode
    3. **Runtime Context**: Filters, tests, and global variables

    Attributes:
        loader: Template source provider (FileSystemLoader, DictLoader, etc.)
        autoescape: HTML auto-escaping. True, False, or callable(name) → bool
        auto_reload: Check template modification times (default: True)
        optimized: Enable compiler optimizations (default: True)
        strict: Raise UndefinedError for undefined variables (default: True)
        strict_none: Fail early on None comparisons during sorting (default: False)
        cache_size: Maximum compiled templates to cache (default: 400)
        fragment_cache_size: Maximum `{% cache %}` fragment entries (default: 1000)
        fragment_ttl: Fragment cache TTL in seconds (default: 300.0)
        globals: Variables available in all templates (includes Python builtins)

    Thread-Safety:
        All operations are safe for concurrent use:
        - Configuration is immutable after `__post_init__`
        - `add_filter()`, `add_test()`, `add_global()` use copy-on-write
        - `get_template()` uses lock-free LRU cache with atomic operations
        - `render()` uses only local state (StringBuilder pattern)

    Strict Mode (Default):
        Undefined variables raise `UndefinedError` instead of returning empty
        string. Catches typos and missing context variables at render time.

        >>> env = Environment()  # strict=True by default
        >>> env.from_string("{{ typo_var }}").render()
        UndefinedError: Undefined variable 'typo_var' in <template>:1

        >>> env.from_string("{{ optional | default('N/A') }}").render()
        'N/A'

    Caching:
        Two LRU caches with configurable sizes:
        - **Template cache**: Compiled Template objects (keyed by name)
        - **Fragment cache**: `{% cache key %}` block outputs (keyed by expression)

        >>> env.cache_info()
        {'template': {'size': 5, 'max_size': 400, 'hits': 100, 'misses': 5},
         'fragment': {'size': 12, 'max_size': 1000, 'hits': 50, 'misses': 12}}

    Example:
        >>> from bengal.rendering.kida import Environment, FileSystemLoader
        >>> env = Environment(
        ...     loader=FileSystemLoader(["templates/", "shared/"]),
        ...     autoescape=True,
        ...     cache_size=100,
        ... )
        >>> env.add_filter("money", lambda x: f"${x:,.2f}")
        >>> env.get_template("invoice.html").render(total=1234.56)
    """

    # Configuration
    loader: Loader | None = None
    autoescape: bool | Callable[[str | None], bool] = True
    auto_reload: bool = True
    optimized: bool = True
    strict: bool = True  # When True, undefined variables raise UndefinedError
    strict_none: bool = False  # When True, sorting with None values raises detailed errors

    # Cache configuration
    cache_size: int = DEFAULT_TEMPLATE_CACHE_SIZE
    fragment_cache_size: int = DEFAULT_FRAGMENT_CACHE_SIZE
    fragment_ttl: float = DEFAULT_FRAGMENT_TTL

    # Bytecode cache (optional, for persistent template caching)
    bytecode_cache: BytecodeCache | None = None

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

    # Template cache (LRU with size limit)
    _cache: LRUCache = field(init=False)
    _fragment_cache: LRUCache = field(init=False)

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

        # Initialize LRU caches (uses shared bengal.utils.lru_cache.LRUCache)
        self._cache: LRUCache[str, Template] = LRUCache(
            maxsize=self.cache_size,
            name="kida_template",
        )
        self._fragment_cache: LRUCache[str, str] = LRUCache(
            maxsize=self.fragment_cache_size,
            ttl=self.fragment_ttl,
            name="kida_fragment",
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

    def add_global(self, name: str, value: Any) -> None:
        """Add a global variable (copy-on-write).

        Args:
            name: Global name (used in templates as {{ name }})
            value: Any value (variable, function, etc.)
        """
        new_globals = self.globals.copy()
        new_globals[name] = value
        self.globals = new_globals

    def update_filters(self, filters: dict[str, Callable]) -> None:
        """Add multiple filters at once (copy-on-write).

        Args:
            filters: Dict mapping filter names to functions

        Example:
            >>> env.update_filters({"double": lambda x: x * 2, "triple": lambda x: x * 3})
        """
        new_filters = self._filters.copy()
        new_filters.update(filters)
        self._filters = new_filters

    def update_tests(self, tests: dict[str, Callable]) -> None:
        """Add multiple tests at once (copy-on-write).

        Args:
            tests: Dict mapping test names to functions

        Example:
            >>> env.update_tests({"positive": lambda x: x > 0, "negative": lambda x: x < 0})
        """
        new_tests = self._tests.copy()
        new_tests.update(tests)
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

        Note:
            With auto_reload=True (default), templates are still cached but
            the cache is checked first. In the future, this may check file
            modification times to invalidate stale entries.
        """
        if self.loader is None:
            raise RuntimeError("No loader configured")

        # Check cache (thread-safe LRU)
        cached = self._cache.get(name)
        if cached is not None:
            # TODO: With auto_reload=True, could check file modification time
            # For now, return cached regardless of auto_reload setting
            return cached

        # Load and compile
        source, filename = self.loader.get_source(name)
        template = self._compile(source, name, filename)

        # Update cache (LRU handles eviction)
        self._cache.set(name, template)

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
        """Compile template source to Template object.

        Applies AST optimizations when self.optimized=True (default).
        Uses bytecode cache when configured for fast cold-start.
        """
        from bengal.rendering.kida.compiler import Compiler
        from bengal.rendering.kida.parser import Parser

        # Check bytecode cache first (for fast cold-start)
        source_hash = None
        if self.bytecode_cache is not None and name is not None:
            from bengal.rendering.kida.bytecode_cache import hash_source

            source_hash = hash_source(source)
            cached_code = self.bytecode_cache.get(name, source_hash)
            if cached_code is not None:
                return Template(self, cached_code, name, filename)

        # Tokenize
        lexer = Lexer(source, self._lexer_config)
        tokens = list(lexer.tokenize())

        # Determine autoescape setting for this template
        should_escape = self.autoescape(name) if callable(self.autoescape) else self.autoescape

        # Parse (pass source for rich error messages)
        parser = Parser(tokens, name, filename, source, autoescape=should_escape)
        ast = parser.parse()

        # Apply AST optimizations
        if self.optimized:
            from bengal.rendering.kida.optimizer import ASTOptimizer

            optimizer = ASTOptimizer()
            result = optimizer.optimize(ast)
            ast = result.ast

        # Compile
        compiler = Compiler(self)
        code = compiler.compile(ast, name, filename)

        # Cache bytecode for future cold-starts
        if self.bytecode_cache is not None and name is not None and source_hash is not None:
            self.bytecode_cache.set(name, source_hash, code)

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

    def clear_cache(self) -> None:
        """Clear all cached templates and fragments.

        Call this to release memory when templates are no longer needed,
        or when template files have been modified and need reloading.

        Example:
            >>> env.clear_cache()
        """
        self._cache.clear()
        self._fragment_cache.clear()

    def clear_template_cache(self) -> None:
        """Clear only the template cache (keep fragment cache)."""
        self._cache.clear()

    def clear_fragment_cache(self) -> None:
        """Clear only the fragment cache (keep template cache)."""
        self._fragment_cache.clear()

    def cache_info(self) -> dict[str, Any]:
        """Return cache statistics.

        Follows Bengal's cache statistics pattern (see DirectiveCache.stats()).

        Returns:
            Dict with cache statistics including hit/miss rates.

        Example:
            >>> info = env.cache_info()
            >>> print(f"Templates: {info['template']['size']}/{info['template']['max_size']}")
            >>> print(f"Template hit rate: {info['template']['hit_rate']:.1%}")
        """
        return {
            "template": self._cache.stats(),
            "fragment": self._fragment_cache.stats(),
        }
