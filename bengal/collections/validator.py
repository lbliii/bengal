"""
Schema validation engine for content collections.

Validates frontmatter dictionaries against dataclass or Pydantic schemas,
with automatic type coercion, helpful error messages, and nested type support.

Key Features:
- **Dual backend support**: Works with Python dataclasses or Pydantic models
- **Type coercion**: Automatically converts strings to datetime, date, etc.
- **Nested validation**: Validates nested dataclass fields recursively
- **Strict mode**: Optionally reject unknown frontmatter fields
- **Detailed errors**: Reports all validation failures, not just the first

Classes:
- :class:`SchemaValidator`: Main validation engine
- :class:`ValidationResult`: Result of schema validation

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
    >>> result = validator.validate({"title": "Hello", "date": "2025-01-15"})
    >>> result.valid
True
    >>> result.data.title
    'Hello'

"""

from __future__ import annotations

from dataclasses import MISSING, dataclass, fields, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

from bengal.collections.errors import ValidationError
from bengal.protocols.capabilities import HasErrors
from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.dates import parse_date
from bengal.utils.primitives.types import (
    get_union_args,
    is_optional_type,
    is_union_type,
    type_display_name,
)

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """
    Result of schema validation.

    Encapsulates the outcome of validating frontmatter against a schema,
    including the validated instance (on success) or detailed errors (on failure).

    Attributes:
        valid: ``True`` if validation passed; ``False`` if any errors occurred.
        data: The validated and coerced schema instance (dataclass or Pydantic
            model) on success, or ``None`` if validation failed.
        errors: List of :class:`ValidationError` instances describing each
            field that failed validation. Empty if ``valid`` is ``True``.
        warnings: List of non-fatal warning messages (e.g., deprecated fields).

    Example:
            >>> result = validator.validate({"title": "Hello", "date": "2025-01-15"})
            >>> if result.valid:
            ...     print(result.data.title)
            ... else:
            ...     print(result.error_summary)

    """

    valid: bool
    data: Any | None
    errors: list[ValidationError]
    warnings: list[str]

    @property
    def error_summary(self) -> str:
        """
        Human-readable summary of all validation errors.

        Returns:
            Multi-line string with each error on its own line, formatted as
            ``"  - field: message"``. Returns an empty string if no errors.

        Example:
            >>> print(result.error_summary)
              - title: Required field 'title' is missing
              - date: Cannot parse 'invalid' as datetime
        """
        if not self.errors:
            return ""
        lines = [f"  - {e.field}: {e.message}" for e in self.errors]
        return "\n".join(lines)


class SchemaValidator:
    """
    Validates frontmatter dictionaries against dataclass or Pydantic schemas.

    Supports automatic type coercion, nested validation, and strict mode for
    rejecting unknown fields.

    Supported Schema Types:
        - **Dataclasses**: Python standard library dataclasses (recommended)
        - **Pydantic models**: Auto-detected via ``model_validate`` method

    Type Coercion:
        The validator automatically coerces common types:

        - ``datetime``: From ISO 8601 strings (e.g., ``"2025-01-15T10:30:00"``)
        - ``date``: From ISO 8601 date strings (e.g., ``"2025-01-15"``)
        - ``bool``: From strings (``"true"``/``"false"``, ``"yes"``/``"no"``)
        - ``int``, ``float``, ``str``: Standard Python coercion
        - ``list[T]``: Validates each item against type ``T``
        - ``Optional[T]``: Accepts ``None`` or validates against ``T``
        - Nested dataclasses: Validates recursively (up to ``max_depth`` levels)

    Attributes:
        schema: The schema class being validated against.
        strict: Whether unknown fields raise errors.
        max_depth: Maximum nesting depth for recursive validation.

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

    Example:
        Strict mode rejects unknown fields:

            >>> validator = SchemaValidator(BlogPost, strict=True)
            >>> result = validator.validate({"title": "Hi", "date": "2025-01-15", "unknown": "value"})
            >>> result.valid
        False
            >>> result.errors[0].field
            'unknown'

    """

    MAX_RECURSION_DEPTH = 10
    """Default maximum nesting depth for recursive dataclass validation."""

    def __init__(
        self,
        schema: type,
        strict: bool = True,
        max_depth: int | None = None,
    ) -> None:
        """
        Initialize a validator for the given schema.

        Args:
            schema: Dataclass or Pydantic model class to validate against.
            strict: If ``True`` (default), reject frontmatter with fields not
                defined in the schema. If ``False``, ignore unknown fields.
            max_depth: Maximum nesting depth for recursive validation.
                Defaults to ``MAX_RECURSION_DEPTH`` (10). Prevents stack
                overflow from deeply nested or malicious input.
        """
        self.schema = schema
        self.strict = strict
        self.max_depth = max_depth if max_depth is not None else self.MAX_RECURSION_DEPTH
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
        Validate frontmatter data against the schema.

        Performs type coercion, checks required fields, validates nested
        structures, and optionally rejects unknown fields (strict mode).

        Args:
            data: Raw frontmatter dictionary parsed from the content file.
            source_file: Optional path to the source file, used for error
                context in logging and exceptions.

        Returns:
            A :class:`ValidationResult` containing:
            - ``valid=True`` and ``data`` set to the validated instance, or
            - ``valid=False`` and ``errors`` listing all validation failures

        Example:
            >>> result = validator.validate({"title": "Hello", "date": "2025-01-15"})
            >>> if result.valid:
            ...     blog_post = result.data
            ... else:
            ...     for error in result.errors:
            ...         print(f"{error.field}: {error.message}")
        """
        # Validate input is a dict
        if data is None:
            return ValidationResult(
                valid=False,
                data=None,
                errors=[
                    ValidationError(
                        field="(root)",
                        message="Expected dict, got None",
                        expected_type="dict",
                    )
                ],
                warnings=[],
            )
        if not isinstance(data, dict):
            return ValidationResult(
                valid=False,
                data=None,
                errors=[
                    ValidationError(
                        field="(root)",
                        message=f"Expected dict, got {type(data).__name__}",
                        value=data,
                        expected_type="dict",
                    )
                ],
                warnings=[],
            )

        if self._is_pydantic:
            return self._validate_pydantic(data, source_file)
        return self._validate_dataclass(data, source_file)

    def _validate_pydantic(
        self,
        data: dict[str, Any],
        source_file: Path | None,
    ) -> ValidationResult:
        """
        Validate data using a Pydantic model.

        Delegates to Pydantic's ``model_validate()`` and converts any
        Pydantic validation errors to our :class:`ValidationError` format.
        """
        try:
            # Type guard: we know schema is Pydantic if _is_pydantic is True
            # Use getattr to avoid mypy error - we've already checked _is_pydantic
            if not self._is_pydantic:
                raise TypeError("Schema is not a Pydantic model")
            # Type ignore: mypy doesn't know that schema has model_validate when _is_pydantic is True
            instance = self.schema.model_validate(data)  # type: ignore[attr-defined]
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
            if isinstance(e, HasErrors):
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
        _depth: int = 0,
    ) -> ValidationResult:
        """
        Validate data using a dataclass schema.

        Iterates through schema fields, coerces types, applies defaults,
        and checks for unknown fields (in strict mode).

        Args:
            data: Dictionary of field values to validate.
            source_file: Optional source file for error context.
            _depth: Current recursion depth (internal use only).
        """
        # Check depth limit before validation
        if _depth > self.max_depth:
            return ValidationResult(
                valid=False,
                data=None,
                errors=[
                    ValidationError(
                        field="(schema)",
                        message=f"Maximum nesting depth ({self.max_depth}) exceeded",
                    )
                ],
                warnings=[],
            )

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
                coerced, type_errors = self._coerce_type(name, value, type_hint, _depth=_depth)

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
                        expected_type=type_display_name(type_hint),
                    )
                )

        # Check for unknown fields (if strict mode)
        if self.strict:
            unknown = set(data.keys()) - set(schema_fields.keys())
            errors.extend(
                ValidationError(
                    field=field_name,
                    message=f"Unknown field '{field_name}' (not in schema)",
                    value=data[field_name],
                )
                for field_name in sorted(unknown)
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
        expected: Any,  # Can be type, generic alias (list[str]), or typing construct
        _depth: int = 0,
    ) -> tuple[Any, list[ValidationError]]:
        """
        Coerce a value to the expected type with error handling.

        Handles complex types including:
        - ``Optional[X]`` / ``X | None``: Accepts None or validates against X
        - ``Union[A, B]`` / ``A | B``: Tries each type in order
        - ``list[X]``: Validates each list item against X
        - ``dict[K, V]``: Validates dict structure (keys/values not yet typed)
        - ``datetime`` / ``date``: Parses from ISO strings or other formats
        - Basic types (``str``, ``int``, ``float``, ``bool``): Standard coercion
        - Nested dataclasses: Recursive validation (up to max_depth)

        Args:
            name: Field name for error messages (may include path, e.g., ``"tags[0]"``).
            value: The value to coerce.
            expected: The expected type (may be a generic like ``list[str]``).
            _depth: Current recursion depth (internal use only).

        Returns:
            Tuple of ``(coerced_value, errors)`` where ``errors`` is empty on
            success or contains :class:`ValidationError` instances on failure.
        """
        origin = get_origin(expected)
        args = get_args(expected)

        # Handle None value
        if value is None:
            if is_optional_type(expected):
                return None, []
            return value, [
                ValidationError(
                    field=name,
                    message="Value cannot be None",
                    value=value,
                    expected_type=type_display_name(expected),
                )
            ]

        # Handle Union types (including Optional[X] and X | Y)
        if is_union_type(expected):
            # Filter out NoneType to get the actual types to validate against
            non_none_args = [a for a in get_union_args(expected) if a is not type(None)]

            if len(non_none_args) == 1:
                # Simple Optional[X] - validate against X
                return self._coerce_type(name, value, non_none_args[0], _depth=_depth)
            else:
                # Union of multiple types - try each until one succeeds
                for arg in non_none_args:
                    result, errors = self._coerce_type(name, value, arg, _depth=_depth)
                    if not errors:
                        return result, []

                return value, [
                    ValidationError(
                        field=name,
                        message=f"Value does not match any type in {type_display_name(expected)}",
                        value=value,
                        expected_type=type_display_name(expected),
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
                    # Lists don't increment depth - only nested dataclasses do
                    coerced, errors = self._coerce_type(
                        f"{name}[{i}]", item, item_type, _depth=_depth
                    )
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
            # Check depth BEFORE creating nested validator
            if _depth >= self.max_depth:
                return value, [
                    ValidationError(
                        field=name,
                        message=f"Maximum nesting depth ({self.max_depth}) exceeded at '{name}'",
                    )
                ]

            if isinstance(value, dict):
                # Pass max_depth to nested validator
                # Type cast: we've already verified expected is a dataclass via is_dataclass()
                nested_validator = SchemaValidator(
                    expected,
                    strict=self.strict,
                    max_depth=self.max_depth,
                )
                # Call internal method with incremented depth
                result = nested_validator._validate_dataclass(value, None, _depth=_depth + 1)
                if result.valid:
                    return result.data, []
                else:
                    # Prefix field names with parent
                    for error in result.errors:
                        error.field = f"{name}.{error.field}"
                    return value, result.errors
            else:
                # Not a dict - can't validate as nested dataclass
                # Get type name safely
                type_name = getattr(expected, "__name__", str(expected))
                return value, [
                    ValidationError(
                        field=name,
                        message=f"Expected dict for nested schema, got {type(value).__name__}",
                        value=value,
                        expected_type=type_name,
                    )
                ]

        # Default: accept as-is if type matches
        # Handle generic types by checking if they are types before calling isinstance
        if isinstance(expected, type) and isinstance(value, expected):
            return value, []

        # Unknown type - log warning and accept as-is
        # This handles complex generics like tuple[str, int] that aren't fully supported
        logger.debug(
            "unknown_type_accepted",
            field=name,
            expected_type=str(expected),
            value_type=type(value).__name__,
            note="Type not fully supported for validation; value accepted as-is",
        )
        return value, []

    def _coerce_datetime(
        self,
        name: str,
        value: Any,
    ) -> tuple[Any, list[ValidationError]]:
        """
        Coerce a value to datetime using the centralized parse_date utility.

        Accepts:
        - ``datetime`` objects (returned as-is)
        - ``date`` objects (converted to datetime at midnight)
        - Strings (parsed via multiple format attempts)

        Returns:
            Tuple of ``(coerced_value, errors)``. On success, returns
            ``(datetime_instance, [])``. On failure, returns ``(None, [error])``.
        """
        # Already a datetime - pass through
        if isinstance(value, datetime):
            return value, []

        # Use centralized date parsing
        result = parse_date(value, on_error="return_none")
        if result is not None:
            return result, []

        return None, [
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
    ) -> tuple[Any, list[ValidationError]]:
        """
        Coerce a value to date using the centralized parse_date utility.

        Accepts:
        - ``date`` objects (returned as-is, unless it's a datetime)
        - ``datetime`` objects (extracts the date portion)
        - Strings (parsed via multiple format attempts)

        Returns:
            Tuple of ``(coerced_value, errors)``. On success, returns
            ``(date_instance, [])``. On failure, returns ``(None, [error])``.
        """
        # Already a date (but not datetime) - pass through
        if isinstance(value, date) and not isinstance(value, datetime):
            return value, []

        # datetime - extract date portion
        if isinstance(value, datetime):
            return value.date(), []

        # Use centralized date parsing and extract date
        result = parse_date(value, on_error="return_none")
        if result is not None:
            return result.date(), []

        return None, [
            ValidationError(
                field=name,
                message=f"Cannot parse '{value}' as date",
                value=value,
                expected_type="date",
            )
        ]
