"""
Collection validation errors.

Provides structured error types for content validation failures, including
detailed error messages with file locations and actionable fix suggestions.

Exception Hierarchy:
    BengalContentError (base)
    ├── ContentValidationError  - Content fails schema validation
    ├── CollectionNotFoundError - Referenced collection doesn't exist
    └── SchemaError             - Schema definition is invalid

All exceptions extend :class:`BengalContentError` for consistent error handling
across the Bengal framework.

Example:
    >>> try:
    ...     validate_frontmatter(page, schema)
    ... except ContentValidationError as e:
    ...     print(f"Validation failed: {e.path}")
    ...     for error in e.errors:
    ...         print(f"  - {error.field}: {error.message}")
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bengal.errors import BengalContentError


@dataclass
class ValidationError:
    """
    A single field-level validation error.

    Represents one validation failure for a specific frontmatter field.
    Multiple ``ValidationError`` instances may be collected into a
    :class:`ContentValidationError` for comprehensive error reporting.

    Attributes:
        field: Name of the field that failed validation. May include array
            indexing for nested errors (e.g., ``"tags[0]"``, ``"author.name"``).
        message: Human-readable description of what went wrong.
        value: The actual value that caused the error. Useful for debugging
            but may be ``None`` for missing required fields.
        expected_type: Expected type as a string (e.g., ``"str"``, ``"list[str]"``).
            Included in the string representation when available.

    Example:
        >>> error = ValidationError(
        ...     field="date",
        ...     message="Cannot parse 'not-a-date' as datetime",
        ...     value="not-a-date",
        ...     expected_type="datetime",
        ... )
        >>> str(error)
        "date: Cannot parse 'not-a-date' as datetime (expected datetime)"
    """

    field: str
    message: str
    value: Any = None
    expected_type: str | None = None

    def __str__(self) -> str:
        """
        Format the error for display.

        Returns:
            Error message with field name, optionally including expected type.
        """
        if self.expected_type:
            return f"{self.field}: {self.message} (expected {self.expected_type})"
        return f"{self.field}: {self.message}"


class ContentValidationError(BengalContentError):
    """
    Raised when content fails schema validation.

    Aggregates multiple :class:`ValidationError` instances with file context,
    providing detailed error information for debugging and user feedback.

    Attributes:
        path: Path to the content file that failed validation.
        errors: List of :class:`ValidationError` instances, one per field failure.
        collection_name: Name of the collection (if known), for context in messages.
        message: Summary error message (inherited from base class).
        suggestion: Optional suggestion for fixing the error.
        original_error: Original exception that caused this error (if any).

    Example:
        >>> try:
        ...     validate_page(page, schema)
        ... except ContentValidationError as e:
        ...     print(e)
        Content validation failed: content/blog/post.md
          └─ title: Required field 'title' is missing
          └─ date: Cannot parse 'not-a-date' as datetime

    Example:
        Converting to JSON for API responses:

        >>> error.to_dict()
        {
            'message': 'Validation failed',
            'path': 'content/blog/post.md',
            'collection': 'blog',
            'errors': [
                {'field': 'title', 'message': 'Required field is missing', ...}
            ]
        }
    """

    def __init__(
        self,
        message: str,
        path: Path,
        errors: list[ValidationError] | None = None,
        collection_name: str | None = None,
        *,
        suggestion: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize a content validation error.

        Args:
            message: Summary error message describing the validation failure.
            path: Path to the content file that failed validation.
            errors: List of :class:`ValidationError` instances for each field
                that failed. May be empty if the error is structural.
            collection_name: Name of the collection being validated, if known.
            suggestion: Actionable suggestion for how to fix the error.
            original_error: The underlying exception, if this error wraps another.
        """
        # Set base class fields
        super().__init__(
            message=message,
            file_path=path,
            suggestion=suggestion,
            original_error=original_error,
        )

        # Set content-specific fields
        self.path = path  # Keep for backward compatibility
        self.errors = errors or []
        self.collection_name = collection_name

    def __str__(self) -> str:
        """
        Format the error with file location and field details.

        Returns:
            Multi-line string with file path, collection name (if known),
            and each field error on its own line with tree-style formatting.
        """
        lines = [f"Content validation failed: {self.path}"]

        if self.collection_name:
            lines[0] += f" (collection: {self.collection_name})"

        for error in self.errors:
            lines.append(f"  └─ {error.field}: {error.message}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.

        Returns:
            Compact repr with path, error count, and collection name.
        """
        return (
            f"ContentValidationError("
            f"path={self.path!r}, "
            f"errors={len(self.errors)}, "
            f"collection={self.collection_name!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the error to a dictionary for JSON serialization.

        Useful for API responses or structured logging.

        Returns:
            Dictionary with keys:
            - ``message``: The summary error message
            - ``path``: File path as a string
            - ``collection``: Collection name or ``None``
            - ``errors``: List of error dicts with ``field``, ``message``,
              ``value`` (repr'd), and ``expected_type``
        """
        return {
            "message": self.message,
            "path": str(self.path),
            "collection": self.collection_name,
            "errors": [
                {
                    "field": e.field,
                    "message": e.message,
                    "value": repr(e.value) if e.value is not None else None,
                    "expected_type": e.expected_type,
                }
                for e in self.errors
            ],
        }


class CollectionNotFoundError(BengalContentError):
    """
    Raised when a referenced collection does not exist.

    Includes the list of available collections to help users identify typos
    or configuration issues.

    Attributes:
        collection_name: Name of the collection that was not found.
        available: List of collection names that do exist.

    Example:
        >>> raise CollectionNotFoundError(
        ...     collection_name="blg",
        ...     available=["blog", "docs", "api"],
        ... )
        CollectionNotFoundError: Collection not found: 'blg'
        Available collections: api, blog, docs
    """

    def __init__(
        self,
        collection_name: str,
        available: list[str] | None = None,
        *,
        suggestion: str | None = None,
    ) -> None:
        """
        Initialize the collection not found error.

        Args:
            collection_name: Name of the collection that was not found.
            available: List of valid collection names for suggestions.
            suggestion: Custom suggestion message. If not provided and
                ``available`` is set, a default suggestion is generated.
        """
        self.collection_name = collection_name
        self.available = available or []

        message = f"Collection not found: '{collection_name}'"
        if self.available:
            message += f"\nAvailable collections: {', '.join(sorted(self.available))}"

        # Generate suggestion if not provided
        if suggestion is None and self.available:
            suggestion = f"Available collections: {', '.join(sorted(self.available))}"

        super().__init__(
            message=message,
            suggestion=suggestion,
        )


class SchemaError(BengalContentError):
    """
    Raised when a schema definition is invalid.

    Indicates a problem with the schema class itself (e.g., invalid type hints,
    conflicting defaults), not with the content being validated against it.

    Attributes:
        schema_name: Name of the invalid schema class.

    Example:
        >>> raise SchemaError(
        ...     schema_name="BlogPost",
        ...     message="Field 'tags' has invalid default (mutable list)",
        ...     suggestion="Use field(default_factory=list) instead of []",
        ... )
    """

    def __init__(
        self,
        schema_name: str,
        message: str,
        *,
        file_path: Path | None = None,
        suggestion: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize the schema error.

        Args:
            schema_name: Name of the schema class that has the error.
            message: Description of what's wrong with the schema.
            file_path: Path to the file where the schema is defined, if known.
            suggestion: Actionable suggestion for fixing the schema.
            original_error: Underlying exception, if this wraps another error.
        """
        self.schema_name = schema_name
        error_message = f"Invalid schema '{schema_name}': {message}"
        super().__init__(
            message=error_message,
            file_path=file_path,
            suggestion=suggestion,
            original_error=original_error,
        )
