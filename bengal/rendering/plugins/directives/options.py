"""
Typed option parsing for directives.

Provides DirectiveOptions base class for automatic parsing of directive
options with type coercion, validation, and field aliasing.

Architecture:
    Subclass DirectiveOptions with typed fields to get automatic:
    - Parsing from :option: syntax
    - Type coercion (str -> bool, str -> int, str -> list)
    - Validation (via _allowed_values)
    - Default values
    - Self-documentation

Related:
    - bengal/rendering/plugins/directives/base.py: BengalDirective uses these
    - RFC: plan/active/rfc-directive-system-v2.md
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, ClassVar, get_args, get_origin, get_type_hints

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DirectiveOptions:
    """
    Base class for typed directive options.

    Subclass with typed fields to get automatic:
    - Parsing from :option: syntax
    - Type coercion (str -> bool, str -> int, str -> list)
    - Validation (via __post_init__)
    - Default values
    - Self-documentation

    Example:
        @dataclass
        class DropdownOptions(DirectiveOptions):
            open: bool = False
            css_class: str = ""

            _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}

        # Usage:
        opts = DropdownOptions.from_raw({"open": "true", "class": "my-class"})
        # opts.open = True
        # opts.css_class = "my-class"

    Class Variables:
        _field_aliases: Map option names to field names (e.g., {"class": "css_class"})
        _allowed_values: Restrict string fields to specific values
    """

    # Override in subclass to map :option-name: to field_name
    # e.g., {"class": "css_class"} maps :class: to self.css_class
    _field_aliases: ClassVar[dict[str, str]] = {}

    # Override to specify allowed values for string fields
    # e.g., {"gap": ["small", "medium", "large"]}
    _allowed_values: ClassVar[dict[str, list[str]]] = {}

    @classmethod
    def from_raw(cls, raw_options: dict[str, str]) -> DirectiveOptions:
        """
        Parse raw string options into typed instance.

        Handles:
        - Field aliases (:class: -> css_class)
        - Type coercion (str -> bool, int, list)
        - Validation via _allowed_values and __post_init__
        - Unknown options are logged and ignored

        Args:
            raw_options: Dict from mistune's parse_options()

        Returns:
            Typed options instance with defaults applied
        """
        kwargs: dict[str, Any] = {}
        hints = get_type_hints(cls)
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

            # Get target type
            target_type = hints.get(field_name, str)

            # Coerce value
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

    @classmethod
    def _coerce_value(cls, value: str, target_type: type) -> Any:
        """
        Coerce string value to target type.

        Supports:
        - bool: "true", "1", "yes", "" -> True; others -> False
        - int: numeric strings
        - float: numeric strings
        - list[str]: comma-separated values
        - str: pass-through

        Args:
            value: String value from options
            target_type: Target Python type

        Returns:
            Coerced value
        """
        # Handle Optional types (e.g., str | None)
        origin = get_origin(target_type)
        if origin is type(None) or (origin and type(None) in get_args(target_type)):
            # Optional type - extract inner type
            args = get_args(target_type)
            target_type = next((a for a in args if a is not type(None)), str)
            origin = get_origin(target_type)

        if target_type == bool:
            return value.lower() in ("true", "1", "yes", "")

        if target_type == int:
            return int(value) if value.lstrip("-").isdigit() else 0

        if target_type == float:
            try:
                return float(value)
            except ValueError:
                return 0.0

        if origin == list or target_type == list:
            return [v.strip() for v in value.split(",") if v.strip()]

        return value


# =============================================================================
# Pre-built Option Classes for Common Patterns
# =============================================================================


@dataclass
class StyledOptions(DirectiveOptions):
    """
    Common options for styled directives.

    Provides css_class field with :class: alias.

    Example:
        :::{note}
        :class: my-custom-class
        Content
        :::
    """

    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


@dataclass
class ContainerOptions(StyledOptions):
    """
    Options for container-style directives (cards, tabs, etc.).

    Extends StyledOptions with layout options.

    Example:
        :::{cards}
        :columns: 3
        :gap: large
        :style: bordered
        :::
    """

    columns: str = "auto"
    gap: str = "medium"
    style: str = "default"

    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "gap": ["small", "medium", "large"],
        "style": ["default", "minimal", "bordered"],
    }


@dataclass
class TitledOptions(StyledOptions):
    """
    Options for directives with optional title.

    Extends StyledOptions with icon support.

    Example:
        :::{card} Card Title
        :icon: star
        Content
        :::
    """

    icon: str = ""

