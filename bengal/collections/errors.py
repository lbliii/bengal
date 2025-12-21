"""
Collection validation errors.

Provides structured error types for content validation failures with
helpful error messages including file locations and fix suggestions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bengal.errors import BengalContentError


@dataclass
class ValidationError:
    """
    A single validation error for a frontmatter field.

    Attributes:
        field: Name of the field that failed validation (e.g., "title", "tags[0]")
        message: Human-readable error description
        value: The actual value that caused the error (for debugging)
        expected_type: Expected type description (e.g., "str", "list[str]")
    """

    field: str
    message: str
    value: Any = None
    expected_type: str | None = None

    def __str__(self) -> str:
        """Format error for display."""
        if self.expected_type:
            return f"{self.field}: {self.message} (expected {self.expected_type})"
        return f"{self.field}: {self.message}"


class ContentValidationError(BengalContentError):
    """
    Raised when content fails schema validation.

    Provides detailed error information including file location,
    specific field errors, and suggestions for fixing.

    Extends BengalContentError for consistent error handling.

    Attributes:
        path: Path to the content file that failed validation
        errors: List of specific field validation errors
        collection_name: Name of the collection (if known)

    Example:
        >>> try:
        ...     validate_page(page, schema)
        ... except ContentValidationError as e:
        ...     print(e)
        Content validation failed: content/blog/post.md
          └─ title: Required field 'title' is missing
          └─ date: Cannot parse 'not-a-date' as datetime
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
        Initialize content validation error.

        Args:
            message: Summary error message
            path: Path to the content file that failed validation
            errors: List of specific field validation errors
            collection_name: Name of the collection (if known)
            suggestion: Helpful suggestion for fixing
            original_error: Original exception that caused this error
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
        """Format error with file location and field details."""
        lines = [f"Content validation failed: {self.path}"]

        if self.collection_name:
            lines[0] += f" (collection: {self.collection_name})"

        for error in self.errors:
            lines.append(f"  └─ {error.field}: {error.message}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        """Detailed repr for debugging."""
        return (
            f"ContentValidationError("
            f"path={self.path!r}, "
            f"errors={len(self.errors)}, "
            f"collection={self.collection_name!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with error details suitable for JSON output.
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

    Extends BengalContentError for consistent error handling.

    Attributes:
        collection_name: Name of the missing collection
        available: List of available collection names
    """

    def __init__(
        self,
        collection_name: str,
        available: list[str] | None = None,
        *,
        suggestion: str | None = None,
    ) -> None:
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

    This indicates a problem with how the schema was defined,
    not with the content being validated against it.

    Extends BengalContentError for consistent error handling.

    Attributes:
        schema_name: Name of the schema class
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
        self.schema_name = schema_name
        error_message = f"Invalid schema '{schema_name}': {message}"
        super().__init__(
            message=error_message,
            file_path=file_path,
            suggestion=suggestion,
            original_error=original_error,
        )
