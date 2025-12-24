"""Typed option parsing for directive configuration.

This module provides ``DirectiveOptions``, a base class for parsing directive
options from raw strings into typed Python objects. Subclass it with typed
dataclass fields to get automatic parsing, type coercion, validation, and
default values.

Key Features:
    - **Type Coercion**: Automatic conversion from strings to bool, int, float, list.
    - **Field Aliases**: Map directive option names to Python field names
      (e.g., ``:class:`` → ``css_class``).
    - **Validation**: Restrict values to allowed sets via ``_allowed_values``.
    - **Default Values**: Dataclass defaults are used for missing options.

Classes:
    - ``DirectiveOptions``: Base class for typed option parsing.
    - ``StyledOptions``: Preset with ``css_class`` field for CSS classes.
    - ``ContainerOptions``: Preset with layout options (columns, gap, style).
    - ``TitledOptions``: Preset with icon support for titled directives.

Example:
    Define custom options for a directive::

        @dataclass
        class DropdownOptions(DirectiveOptions):
            open: bool = False
            css_class: str = ""

            _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}

        # Parse from raw directive options:
        opts = DropdownOptions.from_raw({"open": "true", "class": "my-class"})
        # opts.open = True
        # opts.css_class = "my-class"

See Also:
    - ``bengal.directives.base``: ``BengalDirective`` uses ``OPTIONS_CLASS``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, fields
from typing import Any, ClassVar, get_args, get_origin, get_type_hints

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DirectiveOptions:
    """Base class for typed directive option parsing.

    Subclass with typed dataclass fields to enable automatic:
        - Parsing from ``:option: value`` syntax.
        - Type coercion (str → bool, int, float, list).
        - Validation via ``_allowed_values``.
        - Default values from field definitions.

    Class Variables:
        _field_aliases: Map option names to field names. Use this when the
            directive option name differs from the Python field name
            (e.g., ``{"class": "css_class"}`` maps ``:class:`` to ``css_class``).
        _allowed_values: Restrict field values to specific sets
            (e.g., ``{"gap": ["small", "medium", "large"]}``).

    Example:
        Define a custom options class::

            @dataclass
            class DropdownOptions(DirectiveOptions):
                open: bool = False
                css_class: str = ""

                _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}

            # Parse from raw options:
            opts = DropdownOptions.from_raw({"open": "true", "class": "my-class"})
            assert opts.open is True
            assert opts.css_class == "my-class"
    """

    _field_aliases: ClassVar[dict[str, str]] = {}
    """Map directive option names to Python field names."""

    _allowed_values: ClassVar[dict[str, list[str]]] = {}
    """Restrict field values to specific allowed sets."""

    # Cached at class definition time
    _cached_hints: ClassVar[dict[str, type]] = {}
    """Cached type hints to avoid repeated get_type_hints() calls."""

    _cached_fields: ClassVar[set[str]] = set()
    """Cached field names to avoid repeated fields() calls."""

    # Pre-compiled coercers for each field
    _coercers: ClassVar[dict[str, Callable[[str], Any]]] = {}
    """Pre-compiled coercion functions to avoid runtime type-checking conditionals."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Pre-compute type hints, fields, and coercers when class is defined.

        This optimization caches type hints, field names, and pre-compiles
        coercion functions at class definition time, avoiding expensive runtime
        calls to get_type_hints(), fields(), and type-checking conditionals
        on every from_raw() invocation.
        """
        super().__init_subclass__(**kwargs)

        # Only cache after @dataclass decorator has run
        # Check for __dataclass_fields__ to confirm dataclass is ready
        if hasattr(cls, "__dataclass_fields__"):
            try:
                cls._cached_hints = get_type_hints(cls)
                cls._cached_fields = {f.name for f in fields(cls) if not f.name.startswith("_")}

                # Pre-compile coercers for each typed field
                cls._coercers = {}
                for name, hint in cls._cached_hints.items():
                    if not name.startswith("_"):
                        cls._coercers[name] = cls._compile_coercer(hint)
            except Exception:
                # Fallback: will compute at runtime
                cls._cached_hints = {}
                cls._cached_fields = set()
                cls._coercers = {}

    @classmethod
    def from_raw(cls, raw_options: dict[str, str]) -> DirectiveOptions:
        """Parse raw string options into a typed instance.

        Processes the raw option dict from Mistune's ``parse_options()`` by:
            1. Resolving field aliases (e.g., ``:class:`` → ``css_class``).
            2. Converting hyphens to underscores in option names.
            3. Coercing string values to target types (bool, int, float, list).
            4. Validating against ``_allowed_values`` if defined.
            5. Ignoring unknown options with a debug log.

        Args:
            raw_options: Dict of string key-value pairs from directive parsing.

        Returns:
            A new instance of the options class with parsed values and defaults.

        Example:
            >>> opts = MyOptions.from_raw({"open": "true", "count": "5"})
            >>> opts.open
            True
            >>> opts.count
            5
        """
        kwargs: dict[str, Any] = {}

        # Ensure cache is populated (for classes defined before __init_subclass__ was added)
        # Check if cache needs population: empty dict/set or not yet computed
        needs_cache = hasattr(cls, "__dataclass_fields__") and (
            not cls._cached_hints
            or len(cls._cached_hints) == 0
            or not cls._cached_fields
            or len(cls._cached_fields) == 0
        )
        if needs_cache:
            try:
                cls._cached_hints = get_type_hints(cls)
                cls._cached_fields = {f.name for f in fields(cls) if not f.name.startswith("_")}
                # Pre-compile coercers if not already done
                if not cls._coercers or len(cls._coercers) == 0:
                    cls._coercers = {}
                    for name, hint in cls._cached_hints.items():
                        if not name.startswith("_"):
                            cls._coercers[name] = cls._compile_coercer(hint)
            except Exception:
                pass  # Fallback to runtime computation

        # Use cached values, with fallback for edge cases
        if cls._cached_hints and len(cls._cached_hints) > 0:
            hints = cls._cached_hints
        else:
            hints = get_type_hints(cls)

        if cls._cached_fields and len(cls._cached_fields) > 0:
            known_fields = cls._cached_fields
        else:
            known_fields = {f.name for f in fields(cls) if not f.name.startswith("_")}

        for raw_name, raw_value in raw_options.items():
            # Resolve alias
            field_name = cls._field_aliases.get(raw_name, raw_name.replace("-", "_"))

            if field_name not in known_fields:
                logger.debug(
                    "directive_unknown_option",
                    option=raw_name,
                    directive=cls.__name__,
                )
                continue

            # Use pre-compiled coercer if available
            coercer = cls._coercers.get(field_name)
            if coercer:
                try:
                    coerced = coercer(raw_value)

                    # Validate allowed values
                    if field_name in cls._allowed_values:
                        allowed = cls._allowed_values[field_name]
                        if coerced not in allowed:
                            logger.warning(
                                "directive_invalid_option_value",
                                option=raw_name,
                                value=raw_value,
                                allowed=allowed,
                                directive=cls.__name__,
                            )
                            continue  # Skip invalid, use default

                    kwargs[field_name] = coerced
                except (ValueError, TypeError):
                    pass  # Use default
            else:
                # Fallback to runtime coercion
                target_type = hints.get(field_name, str)
                try:
                    coerced = cls._coerce_value(raw_value, target_type)

                    # Validate allowed values
                    if field_name in cls._allowed_values:
                        allowed = cls._allowed_values[field_name]
                        if coerced not in allowed:
                            logger.warning(
                                "directive_invalid_option_value",
                                option=raw_name,
                                value=raw_value,
                                allowed=allowed,
                                directive=cls.__name__,
                            )
                            continue  # Skip invalid, use default

                    kwargs[field_name] = coerced

                except (ValueError, TypeError) as e:
                    logger.warning(
                        "directive_option_coerce_failed",
                        option=raw_name,
                        value=raw_value,
                        target_type=str(target_type),
                        error=str(e),
                    )

        return cls(**kwargs)

    @staticmethod
    def _compile_coercer(target_type: type) -> Callable[[str], Any]:
        """Return a fast coercion function for the target type.

        Pre-compiles coercion logic into a function that avoids runtime
        type-checking conditionals, saving ~30μs per option coercion.

        Args:
            target_type: Target Python type from field annotations.

        Returns:
            A function that takes a string and returns the coerced value.
        """
        # Handle Optional[T] / T | None
        origin = get_origin(target_type)
        if origin is type(None) or (origin and type(None) in get_args(target_type)):
            args = get_args(target_type)
            target_type = next((a for a in args if a is not type(None)), str)
            origin = get_origin(target_type)

        if target_type is bool:
            _truthy = frozenset(("true", "1", "yes", ""))
            return lambda v: v.lower() in _truthy

        if target_type is int:

            def _int_coerce(v: str) -> int:
                return int(v) if v.lstrip("-").isdigit() else 0

            return _int_coerce

        if target_type is float:

            def _float_coerce(v: str) -> float:
                try:
                    return float(v)
                except ValueError:
                    return 0.0

            return _float_coerce

        if origin is list or target_type is list:
            return lambda v: [x.strip() for x in v.split(",") if x.strip()]

        # String passthrough (identity function)
        return lambda v: v

    @classmethod
    def _coerce_value(cls, value: str, target_type: type) -> Any:
        """Coerce a string value to the target Python type.

        Supported type conversions:
            - ``bool``: ``"true"``, ``"1"``, ``"yes"``, ``""`` → ``True``; else ``False``.
            - ``int``: Numeric strings → int; invalid → 0.
            - ``float``: Numeric strings → float; invalid → 0.0.
            - ``list[str]``: Comma-separated values → list of stripped strings.
            - ``str``: Pass-through unchanged.
            - ``Optional[T]``: Unwraps to inner type ``T``.

        Args:
            value: String value from directive options.
            target_type: Target Python type from field annotations.

        Returns:
            Coerced value matching the target type.
        """
        # Handle Optional types (e.g., str | None)
        origin = get_origin(target_type)
        if origin is type(None) or (origin and type(None) in get_args(target_type)):
            # Optional type - extract inner type
            args = get_args(target_type)
            target_type = next((a for a in args if a is not type(None)), str)
            origin = get_origin(target_type)

        if target_type is bool:
            return value.lower() in ("true", "1", "yes", "")

        if target_type is int:
            return int(value) if value.lstrip("-").isdigit() else 0

        if target_type is float:
            try:
                return float(value)
            except ValueError:
                return 0.0

        if origin is list or target_type is list:
            return [v.strip() for v in value.split(",") if v.strip()]

        return value


# =============================================================================
# Pre-built Option Classes for Common Patterns
# =============================================================================


@dataclass
class StyledOptions(DirectiveOptions):
    """Common options for styled directives with CSS class support.

    Provides a ``css_class`` field that maps from the ``:class:`` directive
    option. Extend this class for directives that accept custom styling.

    Attributes:
        css_class: Additional CSS classes to apply to the directive output.

    Example:
        ::

            :::{note}
            :class: my-custom-class
            Content here.
            :::
    """

    css_class: str = ""
    """Additional CSS classes (maps from ``:class:``)."""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


@dataclass
class ContainerOptions(StyledOptions):
    """Options for container-style directives with layout controls.

    Extends ``StyledOptions`` with grid layout options for directives like
    cards, tabs, and other multi-item containers.

    Attributes:
        columns: Number of columns or ``"auto"`` for responsive.
        gap: Spacing between items (``"small"``, ``"medium"``, ``"large"``).
        style: Visual style variant (``"default"``, ``"minimal"``, ``"bordered"``).

    Example:
        ::

            :::{cards}
            :columns: 3
            :gap: large
            :style: bordered
            Card content...
            :::
    """

    columns: str = "auto"
    """Number of columns or 'auto' for responsive layout."""

    gap: str = "medium"
    """Spacing between items: 'small', 'medium', or 'large'."""

    style: str = "default"
    """Visual style: 'default', 'minimal', or 'bordered'."""

    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "gap": ["small", "medium", "large"],
        "style": ["default", "minimal", "bordered"],
    }


@dataclass
class TitledOptions(StyledOptions):
    """Options for directives with titles and optional icons.

    Extends ``StyledOptions`` with an icon field for directives that
    display a title with an optional icon (cards, admonitions, etc.).

    Attributes:
        icon: Icon name from the theme's icon library (empty for no icon).

    Example:
        ::

            :::{card} Card Title
            :icon: star
            Card content here.
            :::
    """

    icon: str = ""
    """Icon name from theme icon library (empty for no icon)."""
