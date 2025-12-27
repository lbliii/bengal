"""Built-in tests for Kida templates.

Tests are boolean predicates used with `is` in conditionals:
`{% if value is test %}` or `{% if value is test(arg) %}`

Categories:
    **Type Tests**:
        - `defined`: Value is not None
        - `undefined`: Value is None
        - `none`: Value is None (alias)
        - `string`: Value is a string
        - `number`: Value is int or float (not bool)
        - `sequence`: Value is list, tuple, or string
        - `mapping`: Value is a dict
        - `iterable`: Value supports iteration
        - `callable`: Value is callable

    **Boolean Tests**:
        - `true`: Value is exactly True
        - `false`: Value is exactly False

    **Number Tests**:
        - `odd`: Integer is odd
        - `even`: Integer is even
        - `divisibleby(n)`: Integer is divisible by n

    **Comparison Tests**:
        - `eq(other)` / `equalto(other)`: Equal to other
        - `ne(other)`: Not equal to other
        - `lt(other)` / `lessthan(other)`: Less than other
        - `le(other)`: Less than or equal
        - `gt(other)` / `greaterthan(other)`: Greater than other
        - `ge(other)`: Greater than or equal
        - `sameas(other)`: Identity comparison (is)
        - `in(seq)`: Value is in sequence

    **String Tests**:
        - `lower`: String is all lowercase
        - `upper`: String is all uppercase

Negation:
    Use `is not` for negated tests:
    `{% if user is not defined %}` or `{% if count is not even %}`

Example:
    ```jinja
    {% if posts is defined and posts is iterable %}
        {% for post in posts %}
            {% if loop.index is odd %}
                <div class="odd">{{ post.title }}</div>
            {% endif %}
        {% endfor %}
    {% endif %}
    ```

Custom Tests:
    >>> env.add_test('prime', lambda n: n > 1 and all(n % i for i in range(2, n)))
    >>> # {% if 17 is prime %}Yes{% endif %}
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


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
