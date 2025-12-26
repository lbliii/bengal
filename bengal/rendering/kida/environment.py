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
from bengal.rendering.kida.template import Markup, Template

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
# Filter/Test Registry (Jinja2-compatible interface)
# =============================================================================


class FilterRegistry:
    """Dict-like interface for filters/tests that matches Jinja2's API.

    Supports:
        - env.filters['name'] = func
        - env.filters.update({'name': func})
        - func = env.filters['name']
        - 'name' in env.filters

    All mutations use copy-on-write for thread-safety.
    """

    __slots__ = ("_env", "_attr")

    def __init__(self, env: Environment, attr: str):
        self._env = env
        self._attr = attr

    def _get_dict(self) -> dict[str, Callable]:
        return getattr(self._env, self._attr)

    def _set_dict(self, d: dict[str, Callable]) -> None:
        setattr(self._env, self._attr, d)

    def __getitem__(self, name: str) -> Callable:
        return self._get_dict()[name]

    def __setitem__(self, name: str, func: Callable) -> None:
        new = self._get_dict().copy()
        new[name] = func
        self._set_dict(new)

    def __contains__(self, name: object) -> bool:
        return name in self._get_dict()

    def get(self, name: str, default: Callable | None = None) -> Callable | None:
        return self._get_dict().get(name, default)

    def update(self, mapping: dict[str, Callable]) -> None:
        """Batch update filters (Jinja2 compatibility)."""
        new = self._get_dict().copy()
        new.update(mapping)
        self._set_dict(new)

    def copy(self) -> dict[str, Callable]:
        """Return a copy of the underlying dict."""
        return self._get_dict().copy()

    def keys(self):
        return self._get_dict().keys()

    def values(self):
        return self._get_dict().values()

    def items(self):
        return self._get_dict().items()


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


def _filter_escape(value: Any) -> Markup:
    """HTML-escape the value.

    Returns a Markup object so the result won't be escaped again by autoescape.
    """
    from bengal.rendering.kida.template import Markup

    # Already safe - return as-is
    if isinstance(value, Markup):
        return value

    escaped = (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
    return Markup(escaped)


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


def _filter_safe(value: Any) -> Any:
    """Mark as safe (no escaping)."""
    from bengal.rendering.kida.template import Markup

    return Markup(str(value))


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
    killwords: bool = False,
    end: str = "...",
    leeway: int | None = None,
) -> str:
    """Truncate string to specified length.

    Args:
        value: String to truncate
        length: Maximum length including end marker
        killwords: If False (default), truncate at word boundary; if True, cut mid-word
        end: String to append when truncated (default: "...")
        leeway: Allow slightly longer strings before truncating (Jinja2 compat, ignored)

    Returns:
        Truncated string with end marker if truncated
    """
    value = str(value)
    if len(value) <= length:
        return value

    # Calculate available space for content
    available = length - len(end)
    if available <= 0:
        return end[:length] if length > 0 else ""

    if killwords:
        # Cut mid-word
        return value[:available] + end
    else:
        # Try to break at word boundary
        truncated = value[:available]
        # Find last space
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
        return truncated.rstrip() + end


def _filter_upper(value: str) -> str:
    """Convert to uppercase."""
    return str(value).upper()


def _filter_tojson(value: Any, indent: int | None = None) -> Any:
    """Convert value to JSON string (marked safe to prevent escaping)."""
    import json

    from bengal.rendering.kida.template import Markup

    return Markup(json.dumps(value, indent=indent, default=str))


def _filter_batch(value: Any, linecount: int, fill_with: Any = None) -> list:
    """Batch items into groups of linecount."""
    result = []
    batch: list = []
    for item in value:
        batch.append(item)
        if len(batch) >= linecount:
            result.append(batch)
            batch = []
    if batch:
        if fill_with is not None:
            while len(batch) < linecount:
                batch.append(fill_with)
        result.append(batch)
    return result


def _filter_slice(value: Any, slices: int, fill_with: Any = None) -> list:
    """Slice items into number of groups."""
    result: list[list] = [[] for _ in range(slices)]
    for idx, item in enumerate(value):
        result[idx % slices].append(item)
    return result


def _filter_map(
    value: Any,
    *args: Any,
    attribute: str | None = None,
) -> list:
    """Map an attribute or method from a sequence.

    Supports:
        - {{ items|map(attribute='name') }} - extract attribute
        - {{ items|map('upper') }} - call method on each item
    """
    if attribute:
        # Extract attribute from each item
        return [getattr(item, attribute, None) for item in value]
    if args:
        # Call method on each item
        method_name = args[0]
        return [getattr(item, method_name)() for item in value]
    return list(value)


def _filter_selectattr(value: Any, attr: str, *args: Any) -> list:
    """Select items where attribute passes test."""
    result = []
    for item in value:
        val = getattr(item, attr, None)
        if args:
            test_name = args[0]
            test_args = args[1:] if len(args) > 1 else ()
            # Simple test implementations
            if (
                test_name == "equalto"
                and test_args
                and val == test_args[0]
                or test_name == "defined"
                and val is not None
            ):
                result.append(item)
        elif val:
            result.append(item)
    return result


def _filter_rejectattr(value: Any, attr: str, *args: Any) -> list:
    """Reject items where attribute passes test."""
    result = []
    for item in value:
        val = getattr(item, attr, None)
        if args:
            test_name = args[0]
            test_args = args[1:] if len(args) > 1 else ()
            if (
                test_name == "equalto"
                and test_args
                and val != test_args[0]
                or test_name == "defined"
                and val is None
            ):
                result.append(item)
        elif not val:
            result.append(item)
    return result


def _apply_test(value: Any, test_name: str, *args: Any) -> bool:
    """Apply a test to a value."""
    if test_name == "defined":
        return value is not None
    if test_name == "undefined":
        return value is None
    if test_name == "none":
        return value is None
    if test_name == "equalto" or test_name == "eq" or test_name == "sameas":
        return args and value == args[0]
    if test_name == "odd":
        return isinstance(value, int) and value % 2 == 1
    if test_name == "even":
        return isinstance(value, int) and value % 2 == 0
    if test_name == "divisibleby":
        return args and isinstance(value, int) and value % args[0] == 0
    if test_name == "iterable":
        try:
            iter(value)
            return True
        except TypeError:
            return False
    if test_name == "mapping":
        return isinstance(value, dict)
    if test_name == "sequence":
        return isinstance(value, (list, tuple, str))
    if test_name == "number":
        return isinstance(value, (int, float))
    if test_name == "string":
        return isinstance(value, str)
    if test_name == "true":
        return value is True
    if test_name == "false":
        return value is False
    # Fallback: truthy check
    return bool(value)


def _filter_select(value: Any, test_name: str | None = None, *args: Any) -> list:
    """Select items that pass a test."""
    if test_name is None:
        return [item for item in value if item]
    return [item for item in value if _apply_test(item, test_name, *args)]


def _filter_reject(value: Any, test_name: str | None = None, *args: Any) -> list:
    """Reject items that pass a test."""
    if test_name is None:
        return [item for item in value if not item]
    return [item for item in value if not _apply_test(item, test_name, *args)]


def _filter_groupby(value: Any, attribute: str) -> list:
    """Group items by attribute."""
    from itertools import groupby

    def get_key(item: Any) -> Any:
        return getattr(item, attribute, None)

    sorted_items = sorted(value, key=get_key)
    return [
        {"grouper": key, "list": list(group)} for key, group in groupby(sorted_items, key=get_key)
    ]


def _filter_striptags(value: str) -> str:
    """Strip HTML tags."""
    import re

    return re.sub(r"<[^>]*>", "", str(value))


def _filter_wordwrap(value: str, width: int = 79, break_long_words: bool = True) -> str:
    """Wrap text at width."""
    import textwrap

    return textwrap.fill(str(value), width=width, break_long_words=break_long_words)


def _filter_indent(value: str, width: int = 4, first: bool = False) -> str:
    """Indent text lines."""
    lines = str(value).splitlines(True)
    indent = " " * width
    if not first:
        return lines[0] + "".join(indent + line for line in lines[1:])
    return "".join(indent + line for line in lines)


def _filter_urlencode(value: str) -> str:
    """URL-encode a string."""
    from urllib.parse import quote

    return quote(str(value), safe="")


def _filter_pprint(value: Any) -> str:
    """Pretty-print a value."""
    from pprint import pformat

    return pformat(value)


def _filter_xmlattr(value: dict) -> str:
    """Convert dict to XML attributes."""
    parts = []
    for key, val in value.items():
        if val is not None:
            escaped = (
                str(val)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )
            parts.append(f'{key}="{escaped}"')
    return " ".join(parts)


def _filter_unique(value: Any, case_sensitive: bool = False, attribute: str | None = None) -> list:
    """Return unique items."""
    seen: set = set()
    result = []
    for item in value:
        val = getattr(item, attribute, None) if attribute else item
        if not case_sensitive and isinstance(val, str):
            val = val.lower()
        if val not in seen:
            seen.add(val)
            result.append(item)
    return result


def _filter_min(value: Any, attribute: str | None = None) -> Any:
    """Return minimum value."""
    if attribute:
        return min(value, key=lambda x: getattr(x, attribute, None))
    return min(value)


def _filter_max(value: Any, attribute: str | None = None) -> Any:
    """Return maximum value."""
    if attribute:
        return max(value, key=lambda x: getattr(x, attribute, None))
    return max(value)


def _filter_sum(value: Any, attribute: str | None = None, start: int = 0) -> Any:
    """Return sum of values."""
    if attribute:
        return sum((getattr(x, attribute, 0) for x in value), start)
    return sum(value, start)


def _filter_attr(value: Any, name: str) -> Any:
    """Get attribute from object."""
    return getattr(value, name, None)


def _filter_format(value: str, *args: Any, **kwargs: Any) -> str:
    """Format string with args/kwargs."""
    return str(value).format(*args, **kwargs)


def _filter_center(value: str, width: int = 80) -> str:
    """Center string in width."""
    return str(value).center(width)


def _filter_round(value: Any, precision: int = 0, method: str = "common") -> float:
    """Round a number to a given precision."""
    if method == "ceil":
        import math

        return math.ceil(float(value) * (10**precision)) / (10**precision)
    elif method == "floor":
        import math

        return math.floor(float(value) * (10**precision)) / (10**precision)
    else:
        return round(float(value), precision)


def _filter_dictsort(
    value: dict,
    case_sensitive: bool = False,
    by: str = "key",
    reverse: bool = False,
) -> list:
    """Sort a dict and return list of (key, value) pairs."""
    if by == "value":

        def sort_key(item: tuple) -> Any:
            val = item[1]
            if not case_sensitive and isinstance(val, str):
                return val.lower()
            return val

    else:

        def sort_key(item: tuple) -> Any:
            val = item[0]
            if not case_sensitive and isinstance(val, str):
                return val.lower()
            return val

    return sorted(value.items(), key=sort_key, reverse=reverse)


def _filter_wordcount(value: str) -> int:
    """Count words in a string."""
    return len(str(value).split())


def _filter_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _filter_filesizeformat(value: int | float, binary: bool = False) -> str:
    """Format a file size as human-readable."""
    bytes_val = float(value)
    base = 1024 if binary else 1000
    prefixes = [
        ("KiB" if binary else "kB", base),
        ("MiB" if binary else "MB", base**2),
        ("GiB" if binary else "GB", base**3),
        ("TiB" if binary else "TB", base**4),
    ]

    if bytes_val < base:
        return f"{int(bytes_val)} Bytes"

    for prefix, divisor in prefixes:
        if bytes_val < divisor * base:
            return f"{bytes_val / divisor:.1f} {prefix}"

    # Fallback to TB
    return f"{bytes_val / (base**4):.1f} {'TiB' if binary else 'TB'}"


# Default filters - comprehensive set matching Jinja2
DEFAULT_FILTERS: dict[str, Callable] = {
    # Basic transformations
    "abs": _filter_abs,
    "capitalize": _filter_capitalize,
    "center": _filter_center,
    "d": _filter_default,
    "default": _filter_default,
    "e": _filter_escape,
    "escape": _filter_escape,
    "first": _filter_first,
    "format": _filter_format,
    "indent": _filter_indent,
    "int": _filter_int,
    "join": _filter_join,
    "last": _filter_last,
    "length": _filter_length,
    "list": _filter_list,
    "lower": _filter_lower,
    "pprint": _filter_pprint,
    "replace": _filter_replace,
    "reverse": _filter_reverse,
    "safe": _filter_safe,
    "sort": _filter_sort,
    "string": _filter_string,
    "striptags": _filter_striptags,
    "title": _filter_title,
    "trim": _filter_trim,
    "truncate": _filter_truncate,
    "upper": _filter_upper,
    "urlencode": _filter_urlencode,
    "wordwrap": _filter_wordwrap,
    "xmlattr": _filter_xmlattr,
    # Serialization
    "tojson": _filter_tojson,
    # Collections
    "attr": _filter_attr,
    "batch": _filter_batch,
    "groupby": _filter_groupby,
    "map": _filter_map,
    "max": _filter_max,
    "min": _filter_min,
    "reject": _filter_reject,
    "rejectattr": _filter_rejectattr,
    "select": _filter_select,
    "selectattr": _filter_selectattr,
    "slice": _filter_slice,
    "sum": _filter_sum,
    "unique": _filter_unique,
    # Additional filters
    "count": _filter_length,  # alias
    "dictsort": _filter_dictsort,
    "filesizeformat": _filter_filesizeformat,
    "float": _filter_float,
    "round": _filter_round,
    "strip": _filter_trim,  # alias
    "wordcount": _filter_wordcount,
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
    "false": lambda v: v is False,  # is false test
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
    "true": lambda v: v is True,  # is true test
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
