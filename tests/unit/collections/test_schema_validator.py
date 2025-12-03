"""
Unit tests for SchemaValidator.

Tests dataclass and Pydantic model validation with type coercion,
error handling, and edge cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from bengal.collections.errors import ValidationError
from bengal.collections.validator import SchemaValidator, ValidationResult

# Test schemas


@dataclass
class SimpleSchema:
    """Simple schema with required and optional fields."""

    title: str
    count: int = 0


@dataclass
class BlogPostSchema:
    """Schema mimicking a typical blog post."""

    title: str
    date: datetime
    author: str = "Anonymous"
    tags: list[str] = field(default_factory=list)
    draft: bool = False
    description: str | None = None


@dataclass
class NestedSchema:
    """Schema with nested dataclass."""

    name: str
    metadata: SimpleSchema


@dataclass
class ComplexTypesSchema:
    """Schema with complex type hints."""

    items: list[str]
    mapping: dict[str, Any]
    optional_list: list[int] | None = None


# Basic validation tests


class TestSchemaValidatorBasics:
    """Basic validation functionality."""

    def test_valid_simple_data(self) -> None:
        """Test validation of valid simple data."""
        validator = SchemaValidator(SimpleSchema)
        result = validator.validate({"title": "Hello", "count": 42})

        assert result.valid is True
        assert result.data is not None
        assert result.data.title == "Hello"
        assert result.data.count == 42
        assert result.errors == []

    def test_valid_with_defaults(self) -> None:
        """Test validation uses default values."""
        validator = SchemaValidator(SimpleSchema)
        result = validator.validate({"title": "Hello"})

        assert result.valid is True
        assert result.data.title == "Hello"
        assert result.data.count == 0  # Default

    def test_missing_required_field(self) -> None:
        """Test validation fails for missing required field."""
        validator = SchemaValidator(SimpleSchema)
        result = validator.validate({"count": 42})

        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "title"
        assert "Required field" in result.errors[0].message

    def test_multiple_missing_fields(self) -> None:
        """Test all missing required fields are reported."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({})

        assert result.valid is False
        # Should report both title and date as missing
        missing_fields = {e.field for e in result.errors}
        assert "title" in missing_fields
        assert "date" in missing_fields

    def test_unknown_field_strict_mode(self) -> None:
        """Test unknown fields rejected in strict mode."""
        validator = SchemaValidator(SimpleSchema, strict=True)
        result = validator.validate({"title": "Hello", "unknown_field": "value"})

        assert result.valid is False
        assert any("unknown_field" in e.field for e in result.errors)

    def test_unknown_field_lenient_mode(self) -> None:
        """Test unknown fields allowed in lenient mode."""
        validator = SchemaValidator(SimpleSchema, strict=False)
        result = validator.validate({"title": "Hello", "unknown_field": "value"})

        assert result.valid is True
        assert result.data.title == "Hello"


# Type coercion tests


class TestTypeCoercion:
    """Type coercion functionality."""

    def test_string_to_int(self) -> None:
        """Test string coerced to int."""
        validator = SchemaValidator(SimpleSchema)
        result = validator.validate({"title": "Hello", "count": "42"})

        assert result.valid is True
        assert result.data.count == 42
        assert isinstance(result.data.count, int)

    def test_invalid_string_to_int(self) -> None:
        """Test invalid string fails int coercion."""
        validator = SchemaValidator(SimpleSchema)
        result = validator.validate({"title": "Hello", "count": "not-a-number"})

        assert result.valid is False
        assert any(e.field == "count" for e in result.errors)

    def test_bool_from_string_true(self) -> None:
        """Test bool coerced from string 'true'."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": datetime.now(), "draft": "true"})

        assert result.valid is True
        assert result.data.draft is True

    def test_bool_from_string_false(self) -> None:
        """Test bool coerced from string 'false'."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": datetime.now(), "draft": "false"})

        assert result.valid is True
        assert result.data.draft is False

    def test_bool_from_string_yes(self) -> None:
        """Test bool coerced from string 'yes'."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": datetime.now(), "draft": "yes"})

        assert result.valid is True
        assert result.data.draft is True


# DateTime coercion tests


class TestDateTimeCoercion:
    """DateTime and Date coercion."""

    def test_datetime_passthrough(self) -> None:
        """Test datetime object passes through unchanged."""
        dt = datetime(2025, 1, 15, 10, 30)
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": dt})

        assert result.valid is True
        assert result.data.date == dt

    def test_datetime_from_iso_string(self) -> None:
        """Test datetime parsed from ISO format string."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": "2025-01-15T10:30:00"})

        assert result.valid is True
        assert result.data.date.year == 2025
        assert result.data.date.month == 1
        assert result.data.date.day == 15

    def test_datetime_from_date_string(self) -> None:
        """Test datetime parsed from date-only string."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": "2025-01-15"})

        assert result.valid is True
        assert result.data.date.year == 2025
        assert result.data.date.month == 1
        assert result.data.date.day == 15

    def test_datetime_from_date_object(self) -> None:
        """Test datetime created from date object."""
        d = date(2025, 1, 15)
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": d})

        assert result.valid is True
        assert result.data.date.year == 2025
        assert isinstance(result.data.date, datetime)

    def test_datetime_invalid_string(self) -> None:
        """Test invalid datetime string fails."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": "not-a-date"})

        assert result.valid is False
        assert any("date" in e.field for e in result.errors)


# Date coercion tests


@dataclass
class DateSchema:
    """Schema with date field."""

    published: date


class TestDateCoercion:
    """Date coercion tests."""

    def test_date_passthrough(self) -> None:
        """Test date object passes through unchanged."""
        d = date(2025, 1, 15)
        validator = SchemaValidator(DateSchema)
        result = validator.validate({"published": d})

        assert result.valid is True
        assert result.data.published == d

    def test_date_from_string(self) -> None:
        """Test date parsed from string."""
        validator = SchemaValidator(DateSchema)
        result = validator.validate({"published": "2025-01-15"})

        assert result.valid is True
        assert result.data.published == date(2025, 1, 15)

    def test_date_from_datetime(self) -> None:
        """Test date extracted from datetime."""
        dt = datetime(2025, 1, 15, 10, 30)
        validator = SchemaValidator(DateSchema)
        result = validator.validate({"published": dt})

        assert result.valid is True
        assert result.data.published == date(2025, 1, 15)


# List validation tests


class TestListValidation:
    """List type validation."""

    def test_list_of_strings(self) -> None:
        """Test list of strings validates correctly."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate(
            {"title": "Post", "date": datetime.now(), "tags": ["python", "web"]}
        )

        assert result.valid is True
        assert result.data.tags == ["python", "web"]

    def test_empty_list(self) -> None:
        """Test empty list is valid."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": datetime.now(), "tags": []})

        assert result.valid is True
        assert result.data.tags == []

    def test_list_default_factory(self) -> None:
        """Test list uses default factory when not provided."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": datetime.now()})

        assert result.valid is True
        assert result.data.tags == []

    def test_non_list_fails(self) -> None:
        """Test non-list value fails for list field."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": datetime.now(), "tags": "not-a-list"})

        assert result.valid is False
        assert any("tags" in e.field for e in result.errors)

    def test_list_item_type_coercion(self) -> None:
        """Test list items are type-coerced."""
        validator = SchemaValidator(ComplexTypesSchema)
        result = validator.validate(
            {"items": ["a", "b", "c"], "mapping": {}, "optional_list": ["1", "2", "3"]}
        )

        assert result.valid is True
        # Strings in items should stay strings
        assert result.data.items == ["a", "b", "c"]
        # Strings in optional_list[int] should be coerced to int
        assert result.data.optional_list == [1, 2, 3]

    def test_list_item_type_error(self) -> None:
        """Test list with invalid item type fails."""
        validator = SchemaValidator(ComplexTypesSchema)
        result = validator.validate({"items": ["a"], "mapping": {}, "optional_list": ["not-int"]})

        assert result.valid is False
        # Error should indicate which item failed
        assert any("optional_list[0]" in e.field for e in result.errors)


# Optional type tests


class TestOptionalTypes:
    """Optional type handling."""

    def test_optional_with_value(self) -> None:
        """Test optional field with value."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate(
            {"title": "Post", "date": datetime.now(), "description": "A description"}
        )

        assert result.valid is True
        assert result.data.description == "A description"

    def test_optional_with_none(self) -> None:
        """Test optional field with explicit None."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": datetime.now(), "description": None})

        assert result.valid is True
        assert result.data.description is None

    def test_optional_omitted(self) -> None:
        """Test optional field omitted uses default."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": datetime.now()})

        assert result.valid is True
        assert result.data.description is None

    def test_optional_list(self) -> None:
        """Test Optional[list[int]] field."""
        validator = SchemaValidator(ComplexTypesSchema)

        # With value
        result = validator.validate({"items": ["a"], "mapping": {}, "optional_list": [1, 2, 3]})
        assert result.valid is True
        assert result.data.optional_list == [1, 2, 3]

        # With None
        result = validator.validate({"items": ["a"], "mapping": {}, "optional_list": None})
        assert result.valid is True
        assert result.data.optional_list is None


# Nested dataclass tests


class TestNestedDataclass:
    """Nested dataclass validation."""

    def test_nested_valid(self) -> None:
        """Test valid nested dataclass."""
        validator = SchemaValidator(NestedSchema)
        result = validator.validate({"name": "Parent", "metadata": {"title": "Child", "count": 10}})

        assert result.valid is True
        assert result.data.name == "Parent"
        assert result.data.metadata.title == "Child"
        assert result.data.metadata.count == 10

    def test_nested_missing_required(self) -> None:
        """Test nested dataclass with missing required field."""
        validator = SchemaValidator(NestedSchema)
        result = validator.validate({"name": "Parent", "metadata": {"count": 10}})

        assert result.valid is False
        # Error should have nested field path
        assert any("metadata.title" in e.field for e in result.errors)

    def test_nested_not_dict(self) -> None:
        """Test nested field must be dict."""
        validator = SchemaValidator(NestedSchema)
        result = validator.validate({"name": "Parent", "metadata": "not-a-dict"})

        # Should fail - can't convert string to nested dataclass
        assert result.valid is False


# ValidationResult tests


class TestValidationResult:
    """ValidationResult properties and methods."""

    def test_error_summary_empty(self) -> None:
        """Test error_summary with no errors."""
        result = ValidationResult(valid=True, data=None, errors=[], warnings=[])
        assert result.error_summary == ""

    def test_error_summary_with_errors(self) -> None:
        """Test error_summary formats errors."""
        errors = [
            ValidationError(field="title", message="Required field 'title' is missing"),
            ValidationError(field="date", message="Cannot parse 'x' as datetime"),
        ]
        result = ValidationResult(valid=False, data=None, errors=errors, warnings=[])

        summary = result.error_summary
        assert "title" in summary
        assert "date" in summary
        assert "Required field" in summary


# Edge cases


class TestEdgeCases:
    """Edge case handling."""

    def test_empty_data(self) -> None:
        """Test validation with empty dict."""
        validator = SchemaValidator(SimpleSchema)
        result = validator.validate({})

        assert result.valid is False
        # Should report title as required
        assert any("title" in e.field for e in result.errors)

    def test_none_value_for_required(self) -> None:
        """Test None value for required field."""
        validator = SchemaValidator(SimpleSchema)
        result = validator.validate({"title": None, "count": 1})

        # None for required string should fail
        assert result.valid is False

    def test_wrong_type_not_coercible(self) -> None:
        """Test wrong type that can't be coerced."""
        validator = SchemaValidator(SimpleSchema)
        result = validator.validate({"title": ["not", "a", "string"], "count": 1})

        # List can't be coerced to string
        assert result.valid is False
        assert any("title" in e.field for e in result.errors)

    def test_source_file_context(self) -> None:
        """Test source_file is accepted for context."""
        validator = SchemaValidator(SimpleSchema)
        result = validator.validate(
            {"title": "Hello"},
            source_file=Path("content/test.md"),
        )

        assert result.valid is True


# Full schema validation


class TestBlogPostSchema:
    """Full blog post schema validation scenarios."""

    def test_minimal_valid_post(self) -> None:
        """Test minimal valid blog post."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "My Post", "date": "2025-01-15"})

        assert result.valid is True
        assert result.data.title == "My Post"
        assert result.data.author == "Anonymous"  # Default
        assert result.data.tags == []  # Default
        assert result.data.draft is False  # Default
        assert result.data.description is None  # Default

    def test_full_valid_post(self) -> None:
        """Test fully populated blog post."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate(
            {
                "title": "My Post",
                "date": "2025-01-15T10:30:00",
                "author": "John Doe",
                "tags": ["python", "bengal", "ssg"],
                "draft": True,
                "description": "A great post about Bengal",
            }
        )

        assert result.valid is True
        assert result.data.title == "My Post"
        assert result.data.author == "John Doe"
        assert result.data.tags == ["python", "bengal", "ssg"]
        assert result.data.draft is True
        assert result.data.description == "A great post about Bengal"

    def test_typical_yaml_frontmatter(self) -> None:
        """Test data as it would come from YAML frontmatter."""
        # Simulating what python-frontmatter would produce
        frontmatter_data = {
            "title": "Getting Started with Bengal",
            "date": "2025-01-15",  # YAML parses dates as strings
            "author": "Jane Smith",
            "tags": ["tutorial", "beginner"],
            "draft": False,
        }

        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate(frontmatter_data)

        assert result.valid is True
        assert result.data.title == "Getting Started with Bengal"
        assert result.data.date.year == 2025
