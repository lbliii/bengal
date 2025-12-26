"""Kida Environment — central configuration and template management.

The Environment is the central hub for:
- Template configuration (delimiters, escaping, etc.)
- Template loading and caching
- Filter and test registration
- Extension management

Thread-Safety:
    The Environment uses copy-on-write for mutable state (filters, tests)
    and lock-free reads. Template caching uses atomic pointer swaps.

Example:
    >>> from kida import Environment
    >>> env = Environment()
    >>> template = env.from_string("Hello, {{ name }}!")
    >>> template.render(name="World")
    'Hello, World!'
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from bengal.rendering.kida.lexer import Lexer, LexerConfig
from bengal.rendering.kida.template import Template

if TYPE_CHECKING:
    pass


# =============================================================================
# Protocols
# =============================================================================


@runtime_checkable
class Loader(Protocol):
    """Protocol for template loaders."""

    def get_source(self, name: str) -> tuple[str, str | None]:
        """Load template source.

        Args:
            name: Template identifier

        Returns:
            Tuple of (source_code, optional_filename)

        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        ...

    def list_templates(self) -> list[str]:
        """List all available templates."""
        ...


@runtime_checkable
class Filter(Protocol):
    """Protocol for template filters."""

    def __call__(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Apply filter to value."""
        ...


@runtime_checkable
class Test(Protocol):
    """Protocol for template tests."""

    def __call__(self, value: Any, *args: Any, **kwargs: Any) -> bool:
        """Test value, return True/False."""
        ...


# =============================================================================
# Loaders
# =============================================================================


class FileSystemLoader:
    """Load templates from the filesystem.

    Example:
        >>> loader = FileSystemLoader("templates")
        >>> source, filename = loader.get_source("index.html")
    """

    __slots__ = ("_paths", "_encoding")

    def __init__(
        self,
        paths: str | Path | list[str | Path],
        encoding: str = "utf-8",
    ):
        if isinstance(paths, (str, Path)):
            paths = [paths]
        self._paths = [Path(p) for p in paths]
        self._encoding = encoding

    def get_source(self, name: str) -> tuple[str, str]:
        """Load template source from filesystem."""
        for base in self._paths:
            path = base / name
            if path.is_file():
                return path.read_text(self._encoding), str(path)

        raise TemplateNotFoundError(
            f"Template '{name}' not found in: {', '.join(str(p) for p in self._paths)}"
        )

    def list_templates(self) -> list[str]:
        """List all templates in search paths."""
        templates = set()
        for base in self._paths:
            if base.is_dir():
                for path in base.rglob("*.html"):
                    templates.add(str(path.relative_to(base)))
                for path in base.rglob("*.xml"):
                    templates.add(str(path.relative_to(base)))
        return sorted(templates)


class DictLoader:
    """Load templates from a dictionary.

    Useful for testing and embedded templates.

    Example:
        >>> loader = DictLoader({"index.html": "Hello, {{ name }}!"})
        >>> source, _ = loader.get_source("index.html")
    """

    __slots__ = ("_mapping",)

    def __init__(self, mapping: dict[str, str]):
        self._mapping = mapping

    def get_source(self, name: str) -> tuple[str, None]:
        if name not in self._mapping:
            raise TemplateNotFoundError(f"Template '{name}' not found")
        return self._mapping[name], None

    def list_templates(self) -> list[str]:
        return sorted(self._mapping.keys())


# =============================================================================
# Exceptions
# =============================================================================


class TemplateError(Exception):
    """Base exception for template errors."""

    pass


class TemplateNotFoundError(TemplateError):
    """Template not found."""

    pass


class TemplateSyntaxError(TemplateError):
    """Template syntax error."""

    def __init__(
        self,
        message: str,
        lineno: int | None = None,
        name: str | None = None,
        filename: str | None = None,
    ):
        self.message = message
        self.lineno = lineno
        self.name = name
        self.filename = filename
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        location = ""
        if self.filename:
            location = f" in {self.filename}"
        if self.lineno:
            location += f" at line {self.lineno}"
        return f"{self.message}{location}"


# =============================================================================
# Built-in Filters
# =============================================================================


def _filter_abs(value: Any) -> Any:
    """Return absolute value."""
    return abs(value)


def _filter_capitalize(value: str) -> str:
    """Capitalize first character."""
    return str(value).capitalize()


def _filter_default(value: Any, default: Any = "", boolean: bool = False) -> Any:
    """Return default if value is undefined or falsy."""
    if boolean:
        return value or default
    return default if value is None else value


def _filter_escape(value: str) -> str:
    """HTML-escape the value."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _filter_first(value: Any) -> Any:
    """Return first item of sequence."""
    return next(iter(value), None)


def _filter_int(value: Any, default: int = 0) -> int:
    """Convert to integer."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _filter_join(value: Any, separator: str = "") -> str:
    """Join sequence with separator."""
    return separator.join(str(x) for x in value)


def _filter_last(value: Any) -> Any:
    """Return last item of sequence."""
    try:
        return list(value)[-1]
    except (IndexError, TypeError):
        return None


def _filter_length(value: Any) -> int:
    """Return length of sequence."""
    return len(value)


def _filter_list(value: Any) -> list:
    """Convert to list."""
    return list(value)


def _filter_lower(value: str) -> str:
    """Convert to lowercase."""
    return str(value).lower()


def _filter_replace(value: str, old: str, new: str, count: int = -1) -> str:
    """Replace occurrences."""
    return str(value).replace(old, new, count if count > 0 else -1)


def _filter_reverse(value: Any) -> Any:
    """Reverse sequence."""
    try:
        return list(reversed(value))
    except TypeError:
        return str(value)[::-1]


def _filter_safe(value: Any) -> str:
    """Mark as safe (no escaping)."""
    # In full implementation, this would return a Markup object
    return str(value)


def _filter_sort(
    value: Any,
    reverse: bool = False,
    key: Callable | None = None,
) -> list:
    """Sort sequence."""
    return sorted(value, reverse=reverse, key=key)


def _filter_string(value: Any) -> str:
    """Convert to string."""
    return str(value)


def _filter_title(value: str) -> str:
    """Title case."""
    return str(value).title()


def _filter_trim(value: str) -> str:
    """Strip whitespace."""
    return str(value).strip()


def _filter_truncate(
    value: str,
    length: int = 255,
    end: str = "...",
) -> str:
    """Truncate string."""
    value = str(value)
    if len(value) <= length:
        return value
    return value[: length - len(end)] + end


def _filter_upper(value: str) -> str:
    """Convert to uppercase."""
    return str(value).upper()


# Default filters
DEFAULT_FILTERS: dict[str, Callable] = {
    "abs": _filter_abs,
    "capitalize": _filter_capitalize,
    "d": _filter_default,
    "default": _filter_default,
    "e": _filter_escape,
    "escape": _filter_escape,
    "first": _filter_first,
    "int": _filter_int,
    "join": _filter_join,
    "last": _filter_last,
    "length": _filter_length,
    "list": _filter_list,
    "lower": _filter_lower,
    "replace": _filter_replace,
    "reverse": _filter_reverse,
    "safe": _filter_safe,
    "sort": _filter_sort,
    "string": _filter_string,
    "title": _filter_title,
    "trim": _filter_trim,
    "truncate": _filter_truncate,
    "upper": _filter_upper,
}


# =============================================================================
# Built-in Tests
# =============================================================================


def _test_callable(value: Any) -> bool:
    """Test if value is callable."""
    return callable(value)


def _test_defined(value: Any) -> bool:
    """Test if value is defined (not None)."""
    return value is not None


def _test_divisible_by(value: int, num: int) -> bool:
    """Test if value is divisible by num."""
    return value % num == 0


def _test_eq(value: Any, other: Any) -> bool:
    """Test equality."""
    return value == other


def _test_even(value: int) -> bool:
    """Test if value is even."""
    return value % 2 == 0


def _test_ge(value: Any, other: Any) -> bool:
    """Test greater than or equal."""
    return value >= other


def _test_gt(value: Any, other: Any) -> bool:
    """Test greater than."""
    return value > other


def _test_in(value: Any, seq: Any) -> bool:
    """Test if value is in sequence."""
    return value in seq


def _test_iterable(value: Any) -> bool:
    """Test if value is iterable."""
    try:
        iter(value)
        return True
    except TypeError:
        return False


def _test_le(value: Any, other: Any) -> bool:
    """Test less than or equal."""
    return value <= other


def _test_lower(value: str) -> bool:
    """Test if string is lowercase."""
    return str(value).islower()


def _test_lt(value: Any, other: Any) -> bool:
    """Test less than."""
    return value < other


def _test_mapping(value: Any) -> bool:
    """Test if value is a mapping."""
    return isinstance(value, dict)


def _test_ne(value: Any, other: Any) -> bool:
    """Test inequality."""
    return value != other


def _test_none(value: Any) -> bool:
    """Test if value is None."""
    return value is None


def _test_number(value: Any) -> bool:
    """Test if value is a number."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _test_odd(value: int) -> bool:
    """Test if value is odd."""
    return value % 2 == 1


def _test_sequence(value: Any) -> bool:
    """Test if value is a sequence."""
    return isinstance(value, (list, tuple, str))


def _test_string(value: Any) -> bool:
    """Test if value is a string."""
    return isinstance(value, str)


def _test_upper(value: str) -> bool:
    """Test if string is uppercase."""
    return str(value).isupper()


# Default tests
DEFAULT_TESTS: dict[str, Callable] = {
    "callable": _test_callable,
    "defined": _test_defined,
    "divisibleby": _test_divisible_by,
    "eq": _test_eq,
    "equalto": _test_eq,
    "even": _test_even,
    "ge": _test_ge,
    "gt": _test_gt,
    "greaterthan": _test_gt,
    "in": _test_in,
    "iterable": _test_iterable,
    "le": _test_le,
    "lower": _test_lower,
    "lt": _test_lt,
    "lessthan": _test_lt,
    "mapping": _test_mapping,
    "ne": _test_ne,
    "none": _test_none,
    "number": _test_number,
    "odd": _test_odd,
    "sameas": lambda v, o: v is o,
    "sequence": _test_sequence,
    "string": _test_string,
    "undefined": lambda v: v is None,
    "upper": _test_upper,
}


# =============================================================================
# Environment
# =============================================================================


@dataclass
class Environment:
    """Central configuration and template management.

    Attributes:
        loader: Template loader (filesystem, dict, etc.)
        autoescape: Auto-escape HTML (default: True for .html/.xml)
        auto_reload: Check template modification times (default: True)
        optimized: Enable compiler optimizations (default: True)

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
    globals: dict[str, Any] = field(default_factory=dict)

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
    def filters(self) -> dict[str, Callable]:
        """Get filters (read-only view)."""
        return self._filters.copy()

    @property
    def tests(self) -> dict[str, Callable]:
        """Get tests (read-only view)."""
        return self._tests.copy()

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

        # Parse
        parser = Parser(tokens, name, filename)
        ast = parser.parse()

        # Compile
        compiler = Compiler(self)
        code = compiler.compile(ast, name, filename)

        return Template(self, code, name, filename)

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
