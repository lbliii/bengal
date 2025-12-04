"""
Unit tests for collection errors.

Tests error formatting, serialization, and error types.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.collections.errors import (
    CollectionNotFoundError,
    ContentValidationError,
    SchemaError,
    ValidationError,
)


class TestValidationError:
    """Tests for ValidationError dataclass."""

    def test_basic_error(self) -> None:
        """Test basic validation error."""
        error = ValidationError(
            field="title",
            message="Required field 'title' is missing",
        )

        assert error.field == "title"
        assert error.message == "Required field 'title' is missing"
        assert error.value is None
        assert error.expected_type is None

    def test_error_with_value(self) -> None:
        """Test validation error with value context."""
        error = ValidationError(
            field="count",
            message="Expected int, got str",
            value="not-a-number",
            expected_type="int",
        )

        assert error.value == "not-a-number"
        assert error.expected_type == "int"

    def test_str_without_expected_type(self) -> None:
        """Test string representation without expected_type."""
        error = ValidationError(
            field="title",
            message="Required field 'title' is missing",
        )

        result = str(error)
        assert "title" in result
        assert "Required field" in result

    def test_str_with_expected_type(self) -> None:
        """Test string representation with expected_type."""
        error = ValidationError(
            field="count",
            message="Expected int, got str",
            expected_type="int",
        )

        result = str(error)
        assert "count" in result
        assert "expected int" in result


class TestContentValidationError:
    """Tests for ContentValidationError exception."""

    def test_basic_exception(self) -> None:
        """Test basic content validation error."""
        error = ContentValidationError(
            message="Validation failed",
            path=Path("content/post.md"),
            errors=[],
        )

        assert error.message == "Validation failed"
        assert error.path == Path("content/post.md")
        assert error.errors == []

    def test_with_field_errors(self) -> None:
        """Test content validation error with field errors."""
        field_errors = [
            ValidationError(field="title", message="Required"),
            ValidationError(field="date", message="Invalid format"),
        ]

        error = ContentValidationError(
            message="Validation failed",
            path=Path("content/post.md"),
            errors=field_errors,
        )

        assert len(error.errors) == 2
        assert error.errors[0].field == "title"
        assert error.errors[1].field == "date"

    def test_with_collection_name(self) -> None:
        """Test content validation error with collection name."""
        error = ContentValidationError(
            message="Validation failed",
            path=Path("content/blog/post.md"),
            errors=[],
            collection_name="blog",
        )

        assert error.collection_name == "blog"

    def test_str_format(self) -> None:
        """Test string format of content validation error."""
        error = ContentValidationError(
            message="Validation failed",
            path=Path("content/post.md"),
            errors=[
                ValidationError(field="title", message="Required field 'title' is missing"),
                ValidationError(field="date", message="Cannot parse as datetime"),
            ],
        )

        result = str(error)

        assert "content/post.md" in result
        assert "title" in result
        assert "date" in result

    def test_str_format_with_collection(self) -> None:
        """Test string format includes collection name."""
        error = ContentValidationError(
            message="Validation failed",
            path=Path("content/blog/post.md"),
            errors=[],
            collection_name="blog",
        )

        result = str(error)
        assert "blog" in result

    def test_repr(self) -> None:
        """Test repr format."""
        error = ContentValidationError(
            message="Validation failed",
            path=Path("content/post.md"),
            errors=[ValidationError(field="x", message="y")],
            collection_name="blog",
        )

        result = repr(error)
        assert "ContentValidationError" in result
        assert "errors=1" in result

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        error = ContentValidationError(
            message="Validation failed",
            path=Path("content/post.md"),
            errors=[
                ValidationError(
                    field="title",
                    message="Required",
                    value=None,
                    expected_type="str",
                ),
            ],
            collection_name="blog",
        )

        result = error.to_dict()

        assert result["message"] == "Validation failed"
        assert result["path"] == "content/post.md"
        assert result["collection"] == "blog"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["field"] == "title"
        assert result["errors"][0]["expected_type"] == "str"

    def test_is_exception(self) -> None:
        """Test that ContentValidationError is an Exception."""
        error = ContentValidationError(
            message="Test error",
            path=Path("test.md"),
            errors=[],
        )

        assert isinstance(error, Exception)

        # Can be raised and caught
        with pytest.raises(ContentValidationError):
            raise error


class TestCollectionNotFoundError:
    """Tests for CollectionNotFoundError exception."""

    def test_basic_error(self) -> None:
        """Test basic collection not found error."""
        error = CollectionNotFoundError("blog")

        assert error.collection_name == "blog"
        assert "blog" in str(error)

    def test_with_available_collections(self) -> None:
        """Test error with available collections hint."""
        error = CollectionNotFoundError(
            "blgo",  # Typo
            available=["blog", "docs", "pages"],
        )

        result = str(error)
        assert "blgo" in result
        assert "blog" in result
        assert "docs" in result

    def test_is_exception(self) -> None:
        """Test that CollectionNotFoundError is an Exception."""
        error = CollectionNotFoundError("missing")

        assert isinstance(error, Exception)

        with pytest.raises(CollectionNotFoundError):
            raise error


class TestSchemaError:
    """Tests for SchemaError exception."""

    def test_basic_error(self) -> None:
        """Test basic schema error."""
        error = SchemaError("BlogPost", "Missing required type hints")

        assert error.schema_name == "BlogPost"
        assert "BlogPost" in str(error)
        assert "Missing required type hints" in str(error)

    def test_is_exception(self) -> None:
        """Test that SchemaError is an Exception."""
        error = SchemaError("TestSchema", "Invalid definition")

        assert isinstance(error, Exception)

        with pytest.raises(SchemaError):
            raise error

