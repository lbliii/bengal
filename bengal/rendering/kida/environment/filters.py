"""Built-in filters for Kida templates.

Filters transform values in template expressions using the pipe syntax:
`{{ value | filter }}` or `{{ value | filter(arg1, arg2) }}`

Categories:
    **String Manipulation**:
        - `capitalize`, `lower`, `upper`, `title`: Case conversion
        - `trim`/`strip`: Remove whitespace
        - `truncate`: Shorten with ellipsis
        - `replace`, `striptags`: Text transformation
        - `center`, `indent`, `wordwrap`: Formatting

    **HTML/Security**:
        - `escape`/`e`: HTML entity encoding (auto-applied with autoescape)
        - `safe`: Mark content as trusted HTML (skip escaping)
        - `striptags`: Remove HTML tags

    **Collections**:
        - `first`, `last`: Get endpoints
        - `length`/`count`: Item count
        - `sort`: Sort sequence (with `attribute=` for objects)
        - `reverse`: Reverse order
        - `unique`: Remove duplicates
        - `batch`, `slice`: Group items
        - `map`, `select`, `reject`: Functional operations
        - `selectattr`, `rejectattr`: Filter by attribute
        - `groupby`: Group by attribute
        - `join`: Concatenate with separator

    **Numbers**:
        - `abs`, `round`, `int`, `float`: Math operations
        - `filesizeformat`: Human-readable file sizes

    **Type Conversion**:
        - `string`, `int`, `float`, `list`: Type coercion
        - `tojson`: JSON serialization (auto-escaped)

    **Debugging**:
        - `debug`: Print variable info to stderr
        - `pprint`: Pretty-print value

    **Validation**:
        - `default`/`d`: Fallback for None/undefined
        - `require`: Raise error if None

None-Resilient Behavior:
    Filters handle None gracefully (like Hugo):
    - `{{ none | default('N/A') }}` → `'N/A'`
    - `{{ none | length }}` → `0`
    - `{{ none | first }}` → `None`

Custom Filters:
    >>> env.add_filter('double', lambda x: x * 2)
    >>> env.add_filter('money', lambda x, currency='$': f'{currency}{x:,.2f}')

    Or with decorator:
    >>> @env.filter()
    ... def reverse_words(s):
    ...     return ' '.join(s.split()[::-1])
"""

from __future__ import annotations

import json
import textwrap
from collections.abc import Callable
from itertools import groupby
from pprint import pformat
from typing import Any
from urllib.parse import quote

from bengal.rendering.kida.environment.exceptions import TemplateRuntimeError
from bengal.rendering.kida.template import Markup
from bengal.rendering.kida.utils.html import (
    html_escape_filter,
    spaceless,
    strip_tags,
    xmlattr,
)


def _filter_abs(value: Any) -> Any:
    """Return absolute value."""
    return abs(value)


def _filter_capitalize(value: str) -> str:
    """Capitalize first character."""
    return str(value).capitalize()


def _filter_default(value: Any, default: Any = "", boolean: bool = False) -> Any:
    """Return default if value is undefined or falsy.

    With None-resilient handling, empty string is treated as missing (like None).
    This matches Hugo behavior where nil access returns empty string.
    """
    if boolean:
        return value or default
    # Treat both None and "" as missing (None-resilient compatibility)
    return default if value is None or value == "" else value


def _filter_escape(value: Any) -> Markup:
    """HTML-escape the value.

    Returns a Markup object so the result won't be escaped again by autoescape.
    Uses optimized html_escape_filter from utils.html module.
    """
    return html_escape_filter(value)


def _filter_first(value: Any) -> Any:
    """Return first item of sequence."""
    if value is None:
        return None
    try:
        return next(iter(value), None)
    except (TypeError, ValueError):
        return None


def _filter_int(value: Any, default: int = 0, strict: bool = False) -> int:
    """Convert to integer.
    
    Args:
        value: Value to convert to integer.
        default: Default value to return if conversion fails (default: 0).
        strict: If True, raise TemplateRuntimeError on conversion failure
            instead of returning default (default: False).
    
    Returns:
        Integer value, or default if conversion fails and strict=False.
    
    Raises:
        TemplateRuntimeError: If strict=True and conversion fails.
    
    Examples:
        >>> _filter_int("42")
        42
        >>> _filter_int("not a number")
        0
        >>> _filter_int("not a number", strict=True)
        TemplateRuntimeError: Cannot convert str to int: 'not a number'
    """
    try:
        return int(value)
    except (ValueError, TypeError) as e:
        if strict:
            raise TemplateRuntimeError(
                f"Cannot convert {type(value).__name__} to int: {value!r}",
                suggestion="Use | default(0) | int for optional conversion, or ensure value is numeric",
            ) from e
        return default


def _filter_join(value: Any, separator: str = "") -> str:
    """Join sequence with separator."""
    if value is None:
        return ""
    try:
        return separator.join(str(x) for x in value)
    except (TypeError, ValueError):
        return str(value)


def _filter_last(value: Any) -> Any:
    """Return last item of sequence."""
    if value is None:
        return None
    try:
        return list(value)[-1]
    except (IndexError, TypeError, ValueError):
        return None


def _filter_length(value: Any) -> int:
    """Return length of sequence."""
    if value is None:
        return 0
    try:
        return len(value)
    except (TypeError, ValueError):
        return 0


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


def _filter_safe(value: Any, reason: str | None = None) -> Any:
    """Mark value as safe (no HTML escaping).

    Args:
        value: Content to mark as safe for raw HTML output.
        reason: Optional documentation of why this content is trusted.
            Purely for code review and audit purposes - not used at runtime.

    Example:
        {{ content | safe }}
        {{ user_html | safe(reason="sanitized by bleach library") }}
        {{ cms_block | safe(reason="trusted CMS output, admin-only") }}
    """
    return Markup(str(value))


def _filter_sort(
    value: Any,
    reverse: bool = False,
    case_sensitive: bool = False,
    attribute: str | None = None,
) -> list:
    """Sort sequence with improved error handling for None values.

    When sorting fails due to None comparisons, provides detailed error
    showing which items have None values for the sort attribute.
    """
    from bengal.rendering.kida.environment.exceptions import NoneComparisonError

    if not value:
        return []

    items = list(value)

    # Handle multi-attribute sorting (e.g., "weight,title")
    attributes = attribute.split(",") if attribute else []

    def key_func(item):
        """Generate sort key with None-safe handling.

        Strategy: Use (is_none, sort_value) tuples where:
        - is_none=0 for real values (sort first)
        - is_none=1 for None/empty values (sort last)
        - sort_value is normalized for consistent comparison

        With None-resilient handling, both None and "" are treated as missing.
        """
        if not attributes:
            val = item
            if val is None or val == "":
                return (1, 0, "")  # None/empty sorts last
            if isinstance(val, (int, float)):
                return (0, 0, val)  # Numbers
            val_str = str(val)
            if not case_sensitive:
                val_str = val_str.lower()
            return (0, 1, val_str)  # Strings

        # Build tuple of values for multi-attribute sort
        values = []
        for attr in attributes:
            attr = attr.strip()
            val = _filter_attr(item, attr)

            # Defensive: Handle None and "" (None-resilient) first
            if val is None or val == "":
                # None/empty always sorts last: (1, 0, 0)
                values.append((1, 0, 0))
            elif isinstance(val, (int, float)):
                # Numbers: (0, 0, number) - type 0 means numeric
                values.append((0, 0, val))
            else:
                # Everything else as string: (0, 1, string) - type 1 means string
                # Convert to string safely (handles edge cases)
                try:
                    val_str = str(val)
                    if not case_sensitive:
                        val_str = val_str.lower()
                    values.append((0, 1, val_str))
                except (TypeError, ValueError):
                    # Fallback for unstringable values (shouldn't happen, but be defensive)
                    values.append((1, 0, ""))

        return tuple(values)

    try:
        return sorted(items, reverse=reverse, key=key_func)
    except TypeError as e:
        # Provide detailed error about which items have None/empty values
        error_str = str(e)
        if "NoneType" in error_str or "not supported between" in error_str:
            # Find items with None/empty values for the attribute(s)
            none_items = []
            for idx, item in enumerate(items):
                if attributes:
                    for attr in attributes:
                        attr = attr.strip()
                        val = _filter_attr(item, attr)
                        if val is None or val == "":
                            # Get a representative label for the item
                            item_label = (
                                getattr(item, "title", None)
                                or getattr(item, "name", None)
                                or f"item[{idx}]"
                            )
                            none_items.append(f"  - {item_label}: {attr} = None/empty")
                            break
                else:
                    if item is None or item == "":
                        none_items.append(f"  - item[{idx}] = None/empty")

            attr_str = attribute or "value"
            error_msg = f"Sort failed: cannot compare None values when sorting by '{attr_str}'"
            if none_items:
                error_msg += "\n\nItems with None/empty values:\n" + "\n".join(none_items[:10])
                if len(none_items) > 10:
                    error_msg += f"\n  ... and {len(none_items) - 10} more"
            error_msg += "\n\nSuggestion: Use | default(fallback) on the attribute, or filter out None values first"

            raise NoneComparisonError(
                None,
                None,
                attribute=attribute,
                expression=f"| sort(attribute='{attribute}')" if attribute else "| sort",
            ) from e
        raise


def _filter_string(value: Any) -> str:
    """Convert to string."""
    return str(value)


def _filter_title(value: str) -> str:
    """Title case."""
    return str(value).title()


def _filter_trim(value: str, chars: str | None = None) -> str:
    """Strip whitespace or specified characters.

    Args:
        value: String to trim
        chars: Optional characters to strip (default: whitespace)
    """
    return str(value).strip(chars)


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


def _filter_take(value: Any, count: int) -> list:
    """Take the first N items from a sequence.

    Kida-native filter for readable pipeline operations.

    Example:
        {{ items |> take(5) }}
        {{ posts |> sort(attribute='date', reverse=true) |> take(3) }}

    Args:
        value: Sequence to take from
        count: Number of items to take

    Returns:
        List of first N items (or fewer if sequence is shorter)
    """
    if value is None:
        return []
    try:
        return list(value)[:count]
    except (TypeError, ValueError):
        return []


def _filter_skip(value: Any, count: int) -> list:
    """Skip the first N items from a sequence.

    Kida-native filter for readable pipeline operations.

    Example:
        {{ items |> skip(5) }}
        {{ posts |> skip(10) |> take(10) }}  # pagination

    Args:
        value: Sequence to skip from
        count: Number of items to skip

    Returns:
        List of remaining items after skipping N
    """
    if value is None:
        return []
    try:
        return list(value)[count:]
    except (TypeError, ValueError):
        return []


def _filter_map(
    value: Any,
    *args: Any,
    attribute: str | None = None,
) -> list:
    """Map an attribute or method from a sequence."""
    if value is None:
        return []
    try:
        if attribute:
            return [_filter_attr(item, attribute) for item in value]
        if args:
            method_name = args[0]
            return [getattr(item, method_name)() for item in value]
        return list(value)
    except (TypeError, ValueError):
        return []


def _filter_selectattr(value: Any, attr: str, *args: Any) -> list:
    """Select items where attribute passes test."""
    from bengal.rendering.kida.environment.tests import _apply_test

    result = []
    for item in value:
        val = getattr(item, attr, None)
        if args:
            test_name = args[0]
            test_args = args[1:] if len(args) > 1 else ()
            if _apply_test(val, test_name, *test_args):
                result.append(item)
        elif val:
            result.append(item)
    return result


def _filter_rejectattr(value: Any, attr: str, *args: Any) -> list:
    """Reject items where attribute passes test."""
    from bengal.rendering.kida.environment.tests import _apply_test

    result = []
    for item in value:
        val = getattr(item, attr, None)
        if args:
            test_name = args[0]
            test_args = args[1:] if len(args) > 1 else ()
            if not _apply_test(val, test_name, *test_args):
                result.append(item)
        elif not val:
            result.append(item)
    return result


def _filter_select(value: Any, test_name: str | None = None, *args: Any) -> list:
    """Select items that pass a test."""
    from bengal.rendering.kida.environment.tests import _apply_test

    if test_name is None:
        return [item for item in value if item]
    return [item for item in value if _apply_test(item, test_name, *args)]


def _filter_reject(value: Any, test_name: str | None = None, *args: Any) -> list:
    """Reject items that pass a test."""
    from bengal.rendering.kida.environment.tests import _apply_test

    if test_name is None:
        return [item for item in value if not item]
    return [item for item in value if not _apply_test(item, test_name, *args)]


def _filter_groupby(value: Any, attribute: str) -> list:
    """Group items by attribute."""
    def get_key(item: Any) -> Any:
        return getattr(item, attribute, None)

    sorted_items = sorted(value, key=get_key)
    return [
        {"grouper": key, "list": list(group)} for key, group in groupby(sorted_items, key=get_key)
    ]


def _filter_striptags(value: str) -> str:
    """Strip HTML tags."""
    return strip_tags(value)


def _filter_wordwrap(value: str, width: int = 79, break_long_words: bool = True) -> str:
    """Wrap text at width."""
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
    return quote(str(value), safe="")


def _filter_pprint(value: Any) -> str:
    """Pretty-print a value."""
    return pformat(value)


def _filter_xmlattr(value: dict) -> Markup:
    """Convert dict to XML attributes.
    
    Returns Markup to prevent double-escaping when autoescape is enabled.
    """
    return xmlattr(value)


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
    """Get attribute from object or dictionary key.

    Returns "" for None/missing values (None-resilient, like Hugo).
    """
    if value is None:
        return ""
    # Try dictionary access first (for dict items)
    if isinstance(value, dict):
        val = value.get(name)
        return "" if val is None else val
    # Then try attribute access (for objects)
    try:
        val = getattr(value, name, None)
        return "" if val is None else val
    except (AttributeError, TypeError):
        return ""


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


def _filter_float(value: Any, default: float = 0.0, strict: bool = False) -> float:
    """Convert value to float.
    
    Args:
        value: Value to convert to float.
        default: Default value to return if conversion fails (default: 0.0).
        strict: If True, raise TemplateRuntimeError on conversion failure
            instead of returning default (default: False).
    
    Returns:
        Float value, or default if conversion fails and strict=False.
    
    Raises:
        TemplateRuntimeError: If strict=True and conversion fails.
    
    Examples:
        >>> _filter_float("3.14")
        3.14
        >>> _filter_float("not a number")
        0.0
        >>> _filter_float("not a number", strict=True)
        TemplateRuntimeError: Cannot convert str to float: 'not a number'
    """
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        if strict:
            raise TemplateRuntimeError(
                f"Cannot convert {type(value).__name__} to float: {value!r}",
                suggestion="Use | default(0.0) | float for optional conversion, or ensure value is numeric",
            ) from e
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


def _filter_require(value: Any, message: str | None = None, field_name: str | None = None) -> Any:
    """Require a value to be non-None, raising a clear error if it is.

    Usage:
        {{ user.name | require('User name is required') }}
        {{ config.api_key | require(field_name='api_key') }}

    Args:
        value: The value to check
        message: Custom error message if value is None
        field_name: Field name for the default error message

    Returns:
        The value if not None

    Raises:
        RequiredValueError: If value is None
    """
    from bengal.rendering.kida.environment.exceptions import RequiredValueError

    if value is None:
        raise RequiredValueError(
            field_name=field_name or "value",
            message=message,
        )
    return value


def _filter_debug(value: Any, label: str | None = None, max_items: int = 5) -> Any:
    """Debug filter that prints variable info to stderr and returns the value unchanged.

    Usage:
        {{ posts | debug }}                    -> Shows type and length
        {{ posts | debug('my posts') }}        -> Shows with custom label
        {{ posts | debug(max_items=10) }}      -> Show more items

    Args:
        value: The value to inspect
        label: Optional label for the output
        max_items: Maximum number of items to show for sequences

    Returns:
        The value unchanged (for use in filter chains)

    Output example:
        DEBUG [my posts]: <list[5]>
          [0] Page(title='Getting Started', weight=10)
          [1] Page(title='Installation', weight=None)  <-- None!
          ...
    """
    import sys

    type_name = type(value).__name__
    label_str = f"[{label}]" if label else ""

    # Build output
    lines = []

    if value is None:
        lines.append(f"DEBUG {label_str}: None")
    elif isinstance(value, (list, tuple)):
        lines.append(f"DEBUG {label_str}: <{type_name}[{len(value)}]>")
        for idx, item in enumerate(value[:max_items]):
            item_repr = _debug_repr(item)
            # Flag None values prominently
            none_warning = ""
            if hasattr(item, "__dict__"):
                none_attrs = [
                    k for k, v in vars(item).items() if v is None and not k.startswith("_")
                ]
                if none_attrs:
                    none_warning = f"  <-- None: {', '.join(none_attrs[:3])}"
            lines.append(f"  [{idx}] {item_repr}{none_warning}")
        if len(value) > max_items:
            lines.append(f"  ... ({len(value) - max_items} more items)")
    elif isinstance(value, dict):
        lines.append(f"DEBUG {label_str}: <{type_name}[{len(value)} keys]>")
        for k, v in list(value.items())[:max_items]:
            v_repr = _debug_repr(v)
            none_warning = " <-- None!" if v is None else ""
            lines.append(f"  {k!r}: {v_repr}{none_warning}")
        if len(value) > max_items:
            lines.append(f"  ... ({len(value) - max_items} more keys)")
    elif hasattr(value, "__dict__"):
        # Object with attributes
        attrs = {k: v for k, v in vars(value).items() if not k.startswith("_")}
        lines.append(f"DEBUG {label_str}: <{type_name}>")
        for k, v in list(attrs.items())[:max_items]:
            v_repr = _debug_repr(v)
            none_warning = " <-- None!" if v is None else ""
            lines.append(f"  .{k} = {v_repr}{none_warning}")
        if len(attrs) > max_items:
            lines.append(f"  ... ({len(attrs) - max_items} more attributes)")
    else:
        lines.append(f"DEBUG {label_str}: {_debug_repr(value)} ({type_name})")

    # Print to stderr
    print("\n".join(lines), file=sys.stderr)

    # Return value unchanged for chaining
    return value


def _debug_repr(value: Any, max_len: int = 60) -> str:
    """Create a compact repr for debug output."""
    if value is None:
        return "None"

    type_name = type(value).__name__

    # Special handling for common types
    if hasattr(value, "title"):
        title = getattr(value, "title", None)
        weight = getattr(
            value,
            "weight",
            getattr(value, "metadata", {}).get("weight") if hasattr(value, "metadata") else None,
        )
        if weight is not None:
            return f"{type_name}(title={title!r}, weight={weight})"
        return f"{type_name}(title={title!r})"

    # Truncate long reprs
    r = repr(value)
    if len(r) > max_len:
        return r[: max_len - 3] + "..."
    return r


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
    "skip": _filter_skip,
    "slice": _filter_slice,
    "sum": _filter_sum,
    "take": _filter_take,
    "unique": _filter_unique,
    # Additional filters
    "count": _filter_length,  # alias
    "dictsort": _filter_dictsort,
    "filesizeformat": _filter_filesizeformat,
    "float": _filter_float,
    "round": _filter_round,
    "strip": _filter_trim,  # alias
    "wordcount": _filter_wordcount,
    # Debugging and validation filters
    "require": _filter_require,
    "debug": _filter_debug,
}
