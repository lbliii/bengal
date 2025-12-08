"""
Schema validation engine for content collections.

Validates frontmatter against dataclass or Pydantic schemas with
type coercion, helpful error messages, and support for nested types.
"""

from __future__ import annotations

import logging
import types
from dataclasses import MISSING, dataclass, fields, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Union, get_args, get_origin, get_type_hints

from bengal.collections.errors import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of schema validation.

    Attributes:
        valid: True if validation passed
        data: Validated instance (dataclass or Pydantic model) or None if invalid
        errors: List of validation errors (empty if valid)
        warnings: List of non-fatal warnings
    """

    valid: bool
    data: Any | None
    errors: list[ValidationError]
    warnings: list[str]

    @property
    def error_summary(self) -> str:
        """
        Human-readable summary of all errors.

        Returns:
            Multi-line string with each error on its own line,
            or empty string if no errors.
        """
        if not self.errors:
            return ""
        lines = [f"  - {e.field}: {e.message}" for e in self.errors]
        return "\n".join(lines)


class SchemaValidator:
    """
    Validates frontmatter against dataclass or Pydantic schemas.

    Supports:
    - Dataclass schemas (Python standard library)
    - Pydantic models (optional, auto-detected)
    - Type coercion for common types (datetime, date, lists)
    - Optional/Union types
    - Nested dataclasses
    - Strict mode (reject unknown fields)

    Example:
        >>> from dataclasses import dataclass
        >>> from datetime import datetime
        >>>
        >>> @dataclass
        ... class BlogPost:
        ...     title: str
        ...     date: datetime
        ...     draft: bool = False
        ...
        >>> validator = SchemaValidator(BlogPost)
        >>> result = validator.validate({
        ...     "title": "Hello World",
        ...     "date": "2025-01-15",
        ... })
        >>> result.valid
        True
        >>> result.data.title
        'Hello World'
    """

    def __init__(self, schema: type, strict: bool = True) -> None:
        """
        Initialize validator for a schema.

        Args:
            schema: Dataclass or Pydantic model class
            strict: If True, reject unknown fields in frontmatter
        """
        self.schema = schema
        self.strict = strict
        self._is_pydantic = hasattr(schema, "model_validate")
        self._type_hints: dict[str, Any] = {}

        # Cache type hints for dataclass schemas
        if is_dataclass(schema):
            try:
                self._type_hints = get_type_hints(schema)
            except Exception as e:
                logger.warning(
                    "schema_type_hints_failed",
                    schema=schema.__name__,
                    error=str(e),
                )
                self._type_hints = {}

    def validate(
        self,
        data: dict[str, Any],
        source_file: Path | None = None,
    ) -> ValidationResult:
        """
        Validate frontmatter data against schema.

        Args:
            data: Raw frontmatter dictionary from content file
            source_file: Optional source file path for error context

        Returns:
            ValidationResult with validated data or errors
        """
        if self._is_pydantic:
            return self._validate_pydantic(data, source_file)
        return self._validate_dataclass(data, source_file)

    def _validate_pydantic(
        self,
        data: dict[str, Any],
        source_file: Path | None,
    ) -> ValidationResult:
        """Validate using Pydantic model."""
        try:
            instance = self.schema.model_validate(data)
            return ValidationResult(
                valid=True,
                data=instance,
                errors=[],
                warnings=[],
            )
        except Exception as e:
            # Convert Pydantic errors to our format
            errors: list[ValidationError] = []

            # Pydantic v2 uses .errors() method
            if hasattr(e, "errors"):
                for error in e.errors():
                    field_path = ".".join(str(loc) for loc in error.get("loc", []))
                    errors.append(
                        ValidationError(
                            field=field_path or "(root)",
                            message=error.get("msg", str(error)),
                            value=data.get(error["loc"][0]) if error.get("loc") else None,
                        )
                    )
            else:
                # Fallback for unexpected error format
                errors.append(
                    ValidationError(
                        field="(unknown)",
                        message=str(e),
                    )
                )

            return ValidationResult(
                valid=False,
                data=None,
                errors=errors,
                warnings=[],
            )

    def _validate_dataclass(
        self,
        data: dict[str, Any],
        source_file: Path | None,
    ) -> ValidationResult:
        """Validate using dataclass schema."""
        errors: list[ValidationError] = []
        warnings: list[str] = []
        validated_data: dict[str, Any] = {}

        # Get dataclass fields
        schema_fields = {f.name: f for f in fields(self.schema)}

        # Process each schema field
        for name, field_info in schema_fields.items():
            type_hint = self._type_hints.get(name, Any)

            if name in data:
                # Field present - validate and coerce type
                value = data[name]
                coerced, type_errors = self._coerce_type(name, value, type_hint)

                if type_errors:
                    errors.extend(type_errors)
                else:
                    validated_data[name] = coerced

            elif field_info.default is not MISSING:
                # Use default value
                validated_data[name] = field_info.default

            elif field_info.default_factory is not MISSING:
                # Use default factory
                validated_data[name] = field_info.default_factory()

            else:
                # Required field missing
                errors.append(
                    ValidationError(
                        field=name,
                        message=f"Required field '{name}' is missing",
                        expected_type=self._type_name(type_hint),
                    )
                )

        # Check for unknown fields (if strict mode)
        if self.strict:
            unknown = set(data.keys()) - set(schema_fields.keys())
            for field_name in sorted(unknown):
                errors.append(
                    ValidationError(
                        field=field_name,
                        message=f"Unknown field '{field_name}' (not in schema)",
                        value=data[field_name],
                    )
                )

        # Return early if errors
        if errors:
            return ValidationResult(
                valid=False,
                data=None,
                errors=errors,
                warnings=warnings,
            )

        # Create instance
        try:
            instance = self.schema(**validated_data)
            return ValidationResult(
                valid=True,
                data=instance,
                errors=[],
                warnings=warnings,
            )
        except Exception as e:
            errors.append(
                ValidationError(
                    field="__init__",
                    message=f"Failed to create instance: {e}",
                )
            )
            return ValidationResult(
                valid=False,
                data=None,
                errors=errors,
                warnings=warnings,
            )

    def _coerce_type(
        self,
        name: str,
        value: Any,
        expected: type,
    ) -> tuple[Any, list[ValidationError]]:
        """
        Attempt to coerce value to expected type.

        Handles:
        - Optional[X] (Union[X, None])
        - list[X]
        - datetime and date (from strings)
        - Basic types (str, int, float, bool)

        Args:
            name: Field name (for error messages)
            value: Value to coerce
            expected: Expected type

        Returns:
            Tuple of (coerced_value, list_of_errors)
        """
        origin = get_origin(expected)
        args = get_args(expected)

        # Handle None value
        if value is None:
            if self._is_optional(expected):
                return None, []
            return value, [
                ValidationError(
                    field=name,
                    message="Value cannot be None",
                    value=value,
                    expected_type=self._type_name(expected),
                )
            ]

        # Handle Optional[X] (Union[X, None])
        # Handle both typing.Union and types.UnionType (A | B)
        if origin is Union or origin is types.UnionType:
            # Filter out NoneType
            non_none_args = [a for a in args if a is not type(None)]

            if len(non_none_args) == 1:
                # Simple Optional[X]
                return self._coerce_type(name, value, non_none_args[0])
            else:
                # Union of multiple types - try each
                for arg in non_none_args:
                    result, errors = self._coerce_type(name, value, arg)
                    if not errors:
                        return result, []

                return value, [
                    ValidationError(
                        field=name,
                        message=f"Value does not match any type in {self._type_name(expected)}",
                        value=value,
                        expected_type=self._type_name(expected),
                    )
                ]

        # Handle list[X]
        if origin is list:
            if not isinstance(value, list):
                return value, [
                    ValidationError(
                        field=name,
                        message=f"Expected list, got {type(value).__name__}",
                        value=value,
                        expected_type="list",
                    )
                ]

            if args:
                item_type = args[0]
                coerced_items = []
                all_errors: list[ValidationError] = []

                for i, item in enumerate(value):
                    coerced, errors = self._coerce_type(f"{name}[{i}]", item, item_type)
                    if errors:
                        all_errors.extend(errors)
                    else:
                        coerced_items.append(coerced)

                if all_errors:
                    return value, all_errors
                return coerced_items, []

            return value, []

        # Handle dict[K, V]
        if origin is dict:
            if not isinstance(value, dict):
                return value, [
                    ValidationError(
                        field=name,
                        message=f"Expected dict, got {type(value).__name__}",
                        value=value,
                        expected_type="dict",
                    )
                ]
            # For now, accept dict as-is (could add key/value type checking)
            return value, []

        # Handle datetime
        if expected is datetime:
            return self._coerce_datetime(name, value)

        # Handle date
        if expected is date:
            return self._coerce_date(name, value)

        # Handle basic types
        if expected in (str, int, float, bool):
            if isinstance(value, expected):
                return value, []

            # Bool coercion from strings
            if expected is bool and isinstance(value, str):
                lower = value.lower()
                if lower in ("true", "yes", "1", "on"):
                    return True, []
                if lower in ("false", "no", "0", "off"):
                    return False, []

            # Only coerce between scalar types (not from lists/dicts)
            if isinstance(value, (list, dict, set)):
                return value, [
                    ValidationError(
                        field=name,
                        message=f"Expected {expected.__name__}, got {type(value).__name__}",
                        value=value,
                        expected_type=expected.__name__,
                    )
                ]

            # Attempt coercion for scalar types
            try:
                return expected(value), []
            except (ValueError, TypeError):
                return value, [
                    ValidationError(
                        field=name,
                        message=f"Expected {expected.__name__}, got {type(value).__name__}",
                        value=value,
                        expected_type=expected.__name__,
                    )
                ]

        # Handle nested dataclasses
        if is_dataclass(expected):
            if isinstance(value, dict):
                nested_validator = SchemaValidator(expected, strict=self.strict)
                result = nested_validator.validate(value)
                if result.valid:
                    return result.data, []
                else:
                    # Prefix field names with parent
                    for error in result.errors:
                        error.field = f"{name}.{error.field}"
                    return value, result.errors
            else:
                # Not a dict - can't validate as nested dataclass
                return value, [
                    ValidationError(
                        field=name,
                        message=f"Expected dict for nested schema, got {type(value).__name__}",
                        value=value,
                        expected_type=expected.__name__,
                    )
                ]

        # Default: accept as-is if type matches
        # Handle generic types by checking if they are types before calling isinstance
        if isinstance(expected, type) and isinstance(value, expected):
            return value, []

        # Unknown type - accept as-is with warning
        return value, []

    def _coerce_datetime(
        self,
        name: str,
        value: Any,
    ) -> tuple[datetime | None, list[ValidationError]]:
        """Coerce value to datetime."""
        if isinstance(value, datetime):
            return value, []

        if isinstance(value, date):
            # Convert date to datetime at midnight
            return datetime.combine(value, datetime.min.time()), []

        if isinstance(value, str):
            # Try dateutil parser for flexible parsing
            try:
                from dateutil.parser import parse

                return parse(value), []
            except ImportError:
                pass
            except Exception as e:
                logger.debug(
                    "datetime_parse_failed",
                    field=name,
                    value=value,
                    error=str(e),
                    error_type=type(e).__name__,
                    action="trying_iso_fallback",
                )
                pass

            # Fallback: try ISO format
            try:
                return datetime.fromisoformat(value), []
            except ValueError:
                pass

        return value, [
            ValidationError(
                field=name,
                message=f"Cannot parse '{value}' as datetime",
                value=value,
                expected_type="datetime",
            )
        ]

    def _coerce_date(
        self,
        name: str,
        value: Any,
    ) -> tuple[date | None, list[ValidationError]]:
        """Coerce value to date."""
        if isinstance(value, date) and not isinstance(value, datetime):
            return value, []

        if isinstance(value, datetime):
            return value.date(), []

        if isinstance(value, str):
            # Try dateutil parser
            try:
                from dateutil.parser import parse

                return parse(value).date(), []
            except ImportError:
                pass
            except Exception as e:
                logger.debug(
                    "date_parse_failed",
                    field=name,
                    value=value,
                    error=str(e),
                    error_type=type(e).__name__,
                    action="trying_iso_fallback",
                )
                pass

            # Fallback: try ISO format
            try:
                return date.fromisoformat(value), []
            except ValueError:
                pass

        return value, [
            ValidationError(
                field=name,
                message=f"Cannot parse '{value}' as date",
                value=value,
                expected_type="date",
            )
        ]

    def _is_optional(self, type_hint: type) -> bool:
        """Check if type hint is Optional (Union with None)."""
        origin = get_origin(type_hint)
        if origin is Union or origin is types.UnionType:
            args = get_args(type_hint)
            return type(None) in args
        return False

    def _type_name(self, t: type) -> str:
        """Get human-readable type name."""
        origin = get_origin(t)

        if origin is Union or origin is types.UnionType:
            args = get_args(t)
            # Check for Optional[X]
            if type(None) in args:
                non_none = [a for a in args if a is not type(None)]
                if len(non_none) == 1:
                    return f"Optional[{self._type_name(non_none[0])}]"
            return " | ".join(self._type_name(a) for a in args)

        if origin is list:
            args = get_args(t)
            if args:
                return f"list[{self._type_name(args[0])}]"
            return "list"

        if origin is dict:
            args = get_args(t)
            if args and len(args) >= 2:
                return f"dict[{self._type_name(args[0])}, {self._type_name(args[1])}]"
            return "dict"

        if hasattr(t, "__name__"):
            return t.__name__

        return str(t)
