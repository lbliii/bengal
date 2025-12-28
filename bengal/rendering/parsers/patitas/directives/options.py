"""Typed options system for directive configuration.

Directive options are parsed from :key: value lines in the directive body.
This module provides base classes for type-safe option parsing.

Thread Safety:
    All options classes are frozen dataclasses (immutable).
    Safe to share across threads.

Example:
    >>> @dataclass(frozen=True, slots=True)
    ... class AdmonitionOptions(DirectiveOptions):
    ...     name: str | None = None
    ...     class_: str | None = None
    ...     collapsible: bool = False
    ...
    >>> raw = {"name": "my-note", "collapsible": "true"}
    >>> opts = AdmonitionOptions.from_raw(raw)
    >>> opts.collapsible
    True
"""

from __future__ import annotations

from dataclasses import MISSING, dataclass, fields
from typing import Any, ClassVar, Self, get_type_hints


@dataclass(frozen=True, slots=True)
class DirectiveOptions:
    """Base class for typed directive options.

    Subclass this to define options for your directive. Options are
    automatically parsed from :key: value lines in the directive.

    Type coercion is automatic based on type hints:
    - str: Used as-is
    - bool: "true", "yes", "1", "" → True; others → False
    - int: Parsed with int()
    - float: Parsed with float()
    - list[str]: Split by whitespace

    Thread Safety:
        Frozen dataclass ensures immutability for safe sharing.

    Example:
        >>> @dataclass(frozen=True, slots=True)
        ... class ImageOptions(DirectiveOptions):
        ...     width: int | None = None
        ...     height: int | None = None
        ...     alt: str | None = None
        ...
        >>> opts = ImageOptions.from_raw({"width": "800", "alt": "Photo"})
        >>> opts.width
        800
    """

    # Mapping of option aliases (e.g., "class" -> "class_")
    _aliases: ClassVar[dict[str, str]] = {"class": "class_"}

    @classmethod
    def from_raw(cls, raw: dict[str, str]) -> Self:
        """Parse raw string options into typed values.

        Args:
            raw: Dictionary of raw string options from directive

        Returns:
            Typed options instance

        Raises:
            ValueError: If required option is missing or type coercion fails
        """
        hints = get_type_hints(cls)
        kwargs: dict[str, Any] = {}

        for field in fields(cls):
            # Skip private/internal fields
            if field.name.startswith("_"):
                continue

            # Check for raw value (with alias handling)
            raw_value = None
            if field.name in raw:
                raw_value = raw[field.name]
            else:
                # Check aliases
                for alias, target in cls._aliases.items():
                    if target == field.name and alias in raw:
                        raw_value = raw[alias]
                        break

            if raw_value is not None:
                # Coerce to target type
                target_type = hints.get(field.name, str)
                kwargs[field.name] = cls._coerce(raw_value, target_type, field.name)
            elif field.default is not MISSING:
                kwargs[field.name] = field.default
            elif field.default_factory is not MISSING:
                kwargs[field.name] = field.default_factory()
            # If no default and no raw value, let dataclass handle it
            # (will raise TypeError if field is required)

        return cls(**kwargs)

    @classmethod
    def _coerce(cls, value: str, target_type: type, field_name: str) -> Any:
        """Coerce string value to the target type.

        Args:
            value: Raw string value
            target_type: Target type from type hint
            field_name: Field name for error messages

        Returns:
            Coerced value

        Raises:
            ValueError: If coercion fails
        """
        # Handle Optional types (X | None)
        origin = getattr(target_type, "__origin__", None)
        if origin is type(None):
            return None
        if origin is not None:
            # Union type (e.g., str | None)
            args = getattr(target_type, "__args__", ())
            non_none_args = [a for a in args if a is not type(None)]
            if non_none_args:
                target_type = non_none_args[0]

        # Handle specific types
        if target_type is bool:
            return value.lower() in ("true", "yes", "1", "")

        if target_type is int:
            try:
                return int(value)
            except ValueError as e:
                msg = f"Invalid integer for option '{field_name}': {value}"
                raise ValueError(msg) from e

        if target_type is float:
            try:
                return float(value)
            except ValueError as e:
                msg = f"Invalid float for option '{field_name}': {value}"
                raise ValueError(msg) from e

        if target_type is str:
            return value

        # Handle list[str]
        if origin is list:
            return value.split()

        # Fallback: return as string
        return value


@dataclass(frozen=True, slots=True)
class StyledOptions(DirectiveOptions):
    """Common options for styled directives.

    Provides standard styling options that most directives support:
    - class_: Additional CSS classes
    - name: Reference ID/anchor
    """

    class_: str | None = None
    """Additional CSS classes to apply (:class: option)."""

    name: str | None = None
    """Reference ID for linking (:name: option)."""


@dataclass(frozen=True, slots=True)
class AdmonitionOptions(StyledOptions):
    """Options for admonition directives (note, warning, tip, etc.)."""

    collapsible: bool = False
    """Make admonition collapsible (:collapsible: option)."""

    open: bool = True
    """Start expanded if collapsible (:open: option)."""


@dataclass(frozen=True, slots=True)
class CodeBlockOptions(DirectiveOptions):
    """Options for code-block directive."""

    language: str | None = None
    """Syntax highlighting language."""

    linenos: bool = False
    """Show line numbers."""

    lineno_start: int = 1
    """Starting line number."""

    emphasize_lines: str | None = None
    """Lines to emphasize (comma-separated)."""

    caption: str | None = None
    """Code block caption."""


@dataclass(frozen=True, slots=True)
class ImageOptions(StyledOptions):
    """Options for image directive."""

    width: str | None = None
    """Image width (CSS value)."""

    height: str | None = None
    """Image height (CSS value)."""

    alt: str | None = None
    """Alternative text."""

    align: str | None = None
    """Alignment: left, center, right."""


@dataclass(frozen=True, slots=True)
class FigureOptions(ImageOptions):
    """Options for figure directive (extends ImageOptions)."""

    figwidth: str | None = None
    """Figure container width."""

    figclass: str | None = None
    """CSS class for figure container."""


@dataclass(frozen=True, slots=True)
class TabSetOptions(StyledOptions):
    """Options for tab-set directive."""

    sync_group: str | None = None
    """Sync group for synchronized tabs."""


@dataclass(frozen=True, slots=True)
class TabItemOptions(StyledOptions):
    """Options for tab-item directive."""

    selected: bool = False
    """Tab is selected by default."""

    sync: str | None = None
    """Sync key for this tab."""
