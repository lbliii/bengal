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
        optimized: Deprecated, no-op. Kept for backward compatibility.
        strict: Raise UndefinedError for undefined variables (default: True)
        strict_none: Fail early on None comparisons during sorting (default: False)
        cache_size: Maximum compiled templates to cache (default: 400)
        fragment_cache_size: Maximum `{% cache %}` fragment entries (default: 1000)
        fragment_ttl: Fragment cache TTL in seconds (default: 300.0)
        bytecode_cache: Persistent bytecode cache configuration:
            - None (default): Auto-enabled for FileSystemLoader
            - False: Explicitly disabled
            - BytecodeCache instance: Custom cache directory
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
        Three cache layers for optimal performance:
        - **Bytecode cache** (disk): Persistent compiled bytecode via marshal.
          Auto-enabled for FileSystemLoader in `__pycache__/kida/`.
          Provides 90%+ cold-start improvement for serverless.
        - **Template cache** (memory): Compiled Template objects (keyed by name)
        - **Fragment cache** (memory): `{% cache key %}` block outputs

        >>> env.cache_info()
        {'template': {'size': 5, 'max_size': 400, 'hits': 100, 'misses': 5},
         'fragment': {'size': 12, 'max_size': 1000, 'hits': 50, 'misses': 12},
         'bytecode': {'file_count': 10, 'total_bytes': 45000}}

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

    # Template Introspection (RFC: kida-template-introspection)
    # True (default): Preserve AST, enable block_metadata()/depends_on()
    # False: Discard AST after compilation, save ~2x memory per template
    preserve_ast: bool = True

    # Cache configuration
    cache_size: int = DEFAULT_TEMPLATE_CACHE_SIZE
    fragment_cache_size: int = DEFAULT_FRAGMENT_CACHE_SIZE
    fragment_ttl: float = DEFAULT_FRAGMENT_TTL

    # Bytecode cache for persistent template caching
    # - None (default): Auto-detect from loader (enabled for FileSystemLoader)
    # - False: Explicitly disabled
    # - BytecodeCache instance: User-provided cache
    bytecode_cache: BytecodeCache | bool | None = None

    # Resolved bytecode cache (set in __post_init__)
    _bytecode_cache: BytecodeCache | None = field(init=False, default=None)

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
    # Source hashes for cache invalidation (template_name -> source_hash)
    _template_hashes: dict[str, str] = field(init=False, default_factory=dict)
    # Shared analysis cache (template_name -> TemplateMetadata)
    # Prevents redundant analysis when multiple templates include the same partial
    _analysis_cache: dict[str, Any] = field(init=False, default_factory=dict)

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

        # Resolve bytecode cache
        self._bytecode_cache = self._resolve_bytecode_cache()

    def _resolve_bytecode_cache(self) -> BytecodeCache | None:
        """Resolve bytecode cache from configuration.

        Auto-detection logic:
            - If bytecode_cache is False: disabled
            - If bytecode_cache is BytecodeCache: use it
            - If bytecode_cache is None and loader is FileSystemLoader:
              auto-create cache in first search path's __pycache__/kida/

        Returns:
            Resolved BytecodeCache or None if disabled/unavailable.
        """

        from bengal.rendering.kida.bytecode_cache import BytecodeCache
        from bengal.rendering.kida.environment.loaders import FileSystemLoader

        # Explicit disable
        if self.bytecode_cache is False:
            return None

        # User-provided cache
        if isinstance(self.bytecode_cache, BytecodeCache):
            return self.bytecode_cache

        # Auto-detect from FileSystemLoader
        if isinstance(self.loader, FileSystemLoader) and self.loader._paths:
            # Use __pycache__/kida/ in first search path (follows Python convention)
            cache_dir = self.loader._paths[0] / "__pycache__" / "kida"
            return BytecodeCache(cache_dir)

        # No auto-detection possible (DictLoader, no loader, etc.)
        return None

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
            With auto_reload=True (default), templates are checked for source changes
            using hash comparison. If source changed, cache is invalidated and template
            is reloaded. This ensures templates reflect filesystem changes.
        """
        if self.loader is None:
            raise RuntimeError("No loader configured")

        # Check cache (thread-safe LRU)
        cached = self._cache.get(name)
        if cached is not None:
            # With auto_reload=True, verify source hasn't changed
            if self.auto_reload:
                if self._is_template_stale(name):
                    # Source changed - invalidate cache and reload
                    self._cache.delete(name)
                    self._template_hashes.pop(name, None)
                    self._analysis_cache.pop(name, None)  # Invalidate analysis cache
                else:
                    # Source unchanged - return cached template
                    return cached
            else:
                # auto_reload=False - return cached without checking
                return cached

        # Load and compile
        source, filename = self.loader.get_source(name)

        # Compute source hash for cache invalidation
        from bengal.rendering.kida.bytecode_cache import hash_source

        source_hash = hash_source(source)

        template = self._compile(source, name, filename)

        # Update cache (LRU handles eviction)
        self._cache.set(name, template)
        self._template_hashes[name] = source_hash

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

        Uses bytecode cache when configured for fast cold-start.
        Preserves AST for introspection when self.preserve_ast=True (default).
        """
        from bengal.rendering.kida.compiler import Compiler
        from bengal.rendering.kida.parser import Parser

        # Check bytecode cache first (for fast cold-start)
        source_hash = None
        if self._bytecode_cache is not None and name is not None:
            from bengal.rendering.kida.bytecode_cache import hash_source

            source_hash = hash_source(source)
            cached_code = self._bytecode_cache.get(name, source_hash)
            if cached_code is not None:
                # If introspection is needed, re-parse source to get AST
                # (AST can't be serialized in bytecode cache, so we re-parse)
                optimized_ast = None
                if self.preserve_ast:
                    lexer = Lexer(source, self._lexer_config)
                    tokens = list(lexer.tokenize())
                    should_escape = (
                        self.autoescape(name) if callable(self.autoescape) else self.autoescape
                    )
                    parser = Parser(tokens, name, filename, source, autoescape=should_escape)
                    optimized_ast = parser.parse()

                return Template(self, cached_code, name, filename, optimized_ast=optimized_ast)

        # Tokenize
        lexer = Lexer(source, self._lexer_config)
        tokens = list(lexer.tokenize())

        # Determine autoescape setting for this template
        should_escape = self.autoescape(name) if callable(self.autoescape) else self.autoescape

        # Parse (pass source for rich error messages)
        parser = Parser(tokens, name, filename, source, autoescape=should_escape)
        ast = parser.parse()

        # Preserve AST for introspection if enabled
        optimized_ast = ast if self.preserve_ast else None

        # Compile
        compiler = Compiler(self)
        code = compiler.compile(ast, name, filename)

        # Cache bytecode for future cold-starts
        if self._bytecode_cache is not None and name is not None and source_hash is not None:
            self._bytecode_cache.set(name, source_hash, code)

        return Template(self, code, name, filename, optimized_ast=optimized_ast)

    def _is_template_stale(self, name: str) -> bool:
        """Check if a cached template is stale (source changed).

        Compares current source hash with cached hash. Returns True if:
        - No cached hash exists (first load)
        - Current source hash differs from cached hash

        Args:
            name: Template identifier

        Returns:
            True if template source changed, False if unchanged
        """
        if name not in self._template_hashes:
            # No cached hash - treat as stale to force reload
            return True

        try:
            # Load current source and compute hash
            source, _ = self.loader.get_source(name)
            from bengal.rendering.kida.bytecode_cache import hash_source

            current_hash = hash_source(source)
            cached_hash = self._template_hashes[name]

            # Stale if hashes differ
            return current_hash != cached_hash
        except Exception:
            # If we can't load source (file deleted, etc.), treat as stale
            return True

    def clear_template_cache(self, names: list[str] | None = None) -> None:
        """Clear template cache (optional, for external invalidation).

        Useful when an external system (e.g., Bengal) detects template changes
        and wants to force cache invalidation without waiting for hash check.

        Args:
            names: Specific template names to clear, or None to clear all

        Example:
            >>> env.clear_template_cache()  # Clear all
            >>> env.clear_template_cache(["base.html", "page.html"])  # Clear specific
        """
        if names is None:
            # Clear all templates
            self._cache.clear()
            self._template_hashes.clear()
            self._analysis_cache.clear()
        else:
            # Clear specific templates
            for name in names:
                self._cache.delete(name)
                self._template_hashes.pop(name, None)
                self._analysis_cache.pop(name, None)  # Invalidate analysis cache

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

    def clear_cache(self, include_bytecode: bool = False) -> None:
        """Clear all cached templates and fragments.

        Call this to release memory when templates are no longer needed,
        or when template files have been modified and need reloading.

        Args:
            include_bytecode: Also clear persistent bytecode cache (default: False)

        Example:
            >>> env.clear_cache()  # Clear memory caches only
            >>> env.clear_cache(include_bytecode=True)  # Clear everything
        """
        self._cache.clear()
        self._fragment_cache.clear()
        if include_bytecode and self._bytecode_cache is not None:
            self._bytecode_cache.clear()

    def clear_fragment_cache(self) -> None:
        """Clear only the fragment cache (keep template cache)."""
        self._fragment_cache.clear()

    def clear_bytecode_cache(self) -> int:
        """Clear persistent bytecode cache.

        Returns:
            Number of cache files removed.
        """
        if self._bytecode_cache is not None:
            return self._bytecode_cache.clear()
        return 0

    def cache_info(self) -> dict[str, Any]:
        """Return cache statistics.

        Follows Bengal's cache statistics pattern (see DirectiveCache.stats()).

        Returns:
            Dict with cache statistics including hit/miss rates.

        Example:
            >>> info = env.cache_info()
            >>> print(f"Templates: {info['template']['size']}/{info['template']['max_size']}")
            >>> print(f"Template hit rate: {info['template']['hit_rate']:.1%}")
            >>> if info['bytecode']:
            ...     print(f"Bytecode files: {info['bytecode']['file_count']}")
        """
        info: dict[str, Any] = {
            "template": self._cache.stats(),
            "fragment": self._fragment_cache.stats(),
        }
        if self._bytecode_cache is not None:
            info["bytecode"] = self._bytecode_cache.stats()
        else:
            info["bytecode"] = None
        return info
