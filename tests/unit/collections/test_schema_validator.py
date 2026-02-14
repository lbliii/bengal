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

import pytest

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

    def test_none_input_returns_error(self) -> None:
        """Test None input returns validation error, not crash."""
        validator = SchemaValidator(SimpleSchema)
        result = validator.validate(None)  # type: ignore[arg-type]

        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "(root)"
        assert "dict" in result.errors[0].message
        assert "None" in result.errors[0].message

    def test_non_dict_input_returns_error(self) -> None:
        """Test non-dict input returns validation error, not crash."""
        validator = SchemaValidator(SimpleSchema)

        # Test with string
        result = validator.validate("not a dict")  # type: ignore[arg-type]
        assert result.valid is False
        assert result.errors[0].field == "(root)"
        assert "dict" in result.errors[0].message
        assert "str" in result.errors[0].message

        # Test with list
        result = validator.validate(["a", "list"])  # type: ignore[arg-type]
        assert result.valid is False
        assert "list" in result.errors[0].message

        # Test with int
        result = validator.validate(42)  # type: ignore[arg-type]
        assert result.valid is False
        assert "int" in result.errors[0].message


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


# Recursion depth limit tests


# Pre-defined nested schemas for depth testing (avoids get_type_hints issues)


@dataclass
class Depth1:
    """Flat schema (depth 1)."""

    value: str


@dataclass
class Depth2:
    """Schema with 1 level of nesting (depth 2)."""

    nested: Depth1
    name: str = ""


@dataclass
class Depth3:
    """Schema with 2 levels of nesting (depth 3)."""

    nested: Depth2
    name: str = ""


@dataclass
class Depth4:
    """Schema with 3 levels of nesting (depth 4)."""

    nested: Depth3
    name: str = ""


@dataclass
class Depth5:
    """Schema with 4 levels of nesting (depth 5)."""

    nested: Depth4
    name: str = ""


# Schemas for list nesting tests


@dataclass
class ListItem:
    """Simple item for list tests."""

    value: str


@dataclass
class ListOfNested:
    """Schema with list of nested items."""

    items: list[ListItem]


@dataclass
class InnerMost:
    """Innermost level for list nesting test."""

    value: str


@dataclass
class NestedInList:
    """Middle level for list nesting test."""

    nested: InnerMost


@dataclass
class ListWithNestedLevel:
    """Schema with list containing nested items."""

    items: list[NestedInList]


def _get_schema_for_depth(depth: int) -> type:
    """Get predefined schema for given depth."""
    schemas = {
        1: Depth1,
        2: Depth2,
        3: Depth3,
        4: Depth4,
        5: Depth5,
    }
    if depth not in schemas:
        raise ValueError(f"Only depths 1-5 supported, got {depth}")
    return schemas[depth]


def _generate_nested_data(depth: int) -> dict[str, Any]:
    """Generate nested dictionary data matching the schema depth."""
    if depth <= 1:
        return {"value": "leaf"}

    result: dict[str, Any] = {"name": "level_1"}
    current = result

    for level in range(2, depth):
        current["nested"] = {"name": f"level_{level}"}
        current = current["nested"]

    current["nested"] = {"value": "leaf"}
    return result


class TestRecursionDepthLimit:
    """Tests for max_depth recursion limiting."""

    def test_default_max_depth(self) -> None:
        """Test default max_depth is 10."""
        validator = SchemaValidator(SimpleSchema)
        assert validator.max_depth == 10

    def test_custom_max_depth(self) -> None:
        """Test custom max_depth is respected."""
        validator = SchemaValidator(SimpleSchema, max_depth=5)
        assert validator.max_depth == 5

    def test_nested_within_limit(self) -> None:
        """Test validation passes when nesting is within limit."""
        validator = SchemaValidator(Depth5, max_depth=10)
        data = _generate_nested_data(5)

        result = validator.validate(data)

        assert result.valid is True

    def test_nested_at_exact_limit(self) -> None:
        """Test validation passes when nesting equals limit."""
        # Depth5 has 5 levels, so max_depth=5 should just pass
        validator = SchemaValidator(Depth5, max_depth=5)
        data = _generate_nested_data(5)

        result = validator.validate(data)

        assert result.valid is True

    def test_nested_exceeds_limit(self) -> None:
        """Test validation fails when nesting exceeds limit."""
        # Depth5 has 5 levels, max_depth=3 should fail
        validator = SchemaValidator(Depth5, max_depth=3)
        data = _generate_nested_data(5)

        result = validator.validate(data)

        assert result.valid is False
        assert len(result.errors) >= 1
        assert any("depth" in e.message.lower() for e in result.errors)

    def test_deeply_nested_fails_gracefully(self) -> None:
        """Test deeply nested data returns error, not stack overflow."""
        # Depth5 with max_depth=2 should fail gracefully
        validator = SchemaValidator(Depth5, max_depth=2)
        data = _generate_nested_data(5)

        # Should not raise, should return validation error
        result = validator.validate(data)

        assert result.valid is False
        assert any("depth" in e.message.lower() for e in result.errors)

    def test_max_depth_1_allows_flat(self) -> None:
        """Test max_depth=1 allows flat schemas."""
        validator = SchemaValidator(SimpleSchema, max_depth=1)
        result = validator.validate({"title": "Hello", "count": 42})

        assert result.valid is True

    def test_max_depth_0_rejects_nested(self) -> None:
        """Test max_depth=0 rejects any nesting."""
        # max_depth=0 means no nested dataclasses allowed at all
        validator = SchemaValidator(NestedSchema, max_depth=0)
        result = validator.validate({"name": "Parent", "metadata": {"title": "Child"}})

        assert result.valid is False
        assert any("depth" in e.message.lower() for e in result.errors)

    def test_max_depth_1_allows_one_level_nesting(self) -> None:
        """Test max_depth=1 allows exactly one level of nesting."""
        # NestedSchema has SimpleSchema as a nested field (1 level of nesting)
        validator = SchemaValidator(NestedSchema, max_depth=1)
        result = validator.validate({"name": "Parent", "metadata": {"title": "Child"}})

        assert result.valid is True

    def test_max_depth_1_rejects_two_levels(self) -> None:
        """Test max_depth=1 rejects two levels of nesting."""
        # Depth3 has 3 levels of nesting
        validator = SchemaValidator(Depth3, max_depth=1)
        data = _generate_nested_data(3)

        result = validator.validate(data)

        assert result.valid is False
        assert any("depth" in e.message.lower() for e in result.errors)

    def test_list_of_nested_respects_depth(self) -> None:
        """Test list of nested dataclasses respects depth limit."""
        # Define schemas at module level to avoid get_type_hints issues
        validator = SchemaValidator(ListOfNested, max_depth=2)
        result = validator.validate({"items": [{"value": "a"}, {"value": "b"}]})

        assert result.valid is True

    def test_list_does_not_increment_depth(self) -> None:
        """Test that lists themselves don't count toward depth."""
        # ListWithNestedLevel has list[NestedInList] where NestedInList has InnerMost
        # That's 3 dataclass levels (ListWithNestedLevel -> NestedInList -> InnerMost)
        validator = SchemaValidator(ListWithNestedLevel, max_depth=3)
        data = {"items": [{"nested": {"value": "leaf"}}]}

        result = validator.validate(data)

        assert result.valid is True


# Union type tests


@dataclass
class UnionSchema:
    """Schema with union types."""

    value: str | int
    optional_union: str | int | None = None


class TestUnionTypeCoercion:
    """Tests for union type handling.

    Note: Union coercion tries types in order. For `str | int`, `str` is tried
    first. Since most values can be coerced to str, the first type often wins.
    """

    def test_union_accepts_first_type(self) -> None:
        """Test union accepts the first type (str)."""
        validator = SchemaValidator(UnionSchema)
        result = validator.validate({"value": "hello"})

        assert result.valid is True
        assert result.data.value == "hello"

    def test_union_coerces_to_first_matching_type(self) -> None:
        """Test union coerces to the first type that works.

        For `str | int`, even an int value gets coerced to str since
        str(42) succeeds. This matches how unions try types in order.
        """
        validator = SchemaValidator(UnionSchema)
        result = validator.validate({"value": 42})

        assert result.valid is True
        # Int gets coerced to str since str is first in union
        assert result.data.value == "42"
        assert isinstance(result.data.value, str)

    def test_union_string_stays_string(self) -> None:
        """Test string value stays as string for str | int."""
        validator = SchemaValidator(UnionSchema)
        result = validator.validate({"value": "42"})

        assert result.valid is True
        # Should stay as string
        assert result.data.value == "42"
        assert isinstance(result.data.value, str)

    def test_union_rejects_invalid_type(self) -> None:
        """Test union rejects types that don't match any option."""
        validator = SchemaValidator(UnionSchema)
        result = validator.validate({"value": ["not", "valid"]})

        assert result.valid is False
        assert any("value" in e.field for e in result.errors)

    def test_optional_union_with_none(self) -> None:
        """Test optional union accepts None."""
        validator = SchemaValidator(UnionSchema)
        result = validator.validate({"value": "test", "optional_union": None})

        assert result.valid is True
        assert result.data.optional_union is None

    def test_optional_union_with_string(self) -> None:
        """Test optional union accepts string values."""
        validator = SchemaValidator(UnionSchema)
        result = validator.validate({"value": "test", "optional_union": "hello"})

        assert result.valid is True
        assert result.data.optional_union == "hello"

    def test_optional_union_int_coerced_to_str(self) -> None:
        """Test optional union coerces int to str (first type wins)."""
        validator = SchemaValidator(UnionSchema)
        result = validator.validate({"value": "test", "optional_union": 123})

        assert result.valid is True
        # Int gets coerced to str since str is first in the union
        assert result.data.optional_union == "123"
        assert isinstance(result.data.optional_union, str)


# Test union with int first to show order matters
@dataclass
class IntFirstUnionSchema:
    """Schema with int | str (int first)."""

    value: int | str


class TestUnionOrderMatters:
    """Tests showing that union type order affects coercion."""

    def test_int_first_union_keeps_int(self) -> None:
        """Test int | str keeps int values as int."""
        validator = SchemaValidator(IntFirstUnionSchema)
        result = validator.validate({"value": 42})

        assert result.valid is True
        assert result.data.value == 42
        assert isinstance(result.data.value, int)

    def test_int_first_union_coerces_numeric_string(self) -> None:
        """Test int | str coerces numeric strings to int."""
        validator = SchemaValidator(IntFirstUnionSchema)
        result = validator.validate({"value": "42"})

        assert result.valid is True
        # String "42" gets coerced to int since int is first
        assert result.data.value == 42
        assert isinstance(result.data.value, int)

    def test_int_first_union_falls_back_to_str(self) -> None:
        """Test int | str falls back to str for non-numeric strings."""
        validator = SchemaValidator(IntFirstUnionSchema)
        result = validator.validate({"value": "hello"})

        assert result.valid is True
        # "hello" can't be int, so falls back to str
        assert result.data.value == "hello"
        assert isinstance(result.data.value, str)


# Error message quality tests


class TestErrorMessageQuality:
    """Tests to ensure error messages are helpful and informative."""

    def test_missing_field_mentions_field_name(self) -> None:
        """Test that missing field errors include the field name."""
        validator = SchemaValidator(SimpleSchema)
        result = validator.validate({})

        assert result.valid is False
        assert any("title" in e.message for e in result.errors)

    def test_type_error_mentions_expected_type(self) -> None:
        """Test that type errors mention the expected type."""
        validator = SchemaValidator(SimpleSchema)
        result = validator.validate({"title": ["not", "a", "string"], "count": 1})

        assert result.valid is False
        error = next(e for e in result.errors if e.field == "title")
        assert error.expected_type == "str"

    def test_type_error_mentions_actual_type(self) -> None:
        """Test that type errors mention the actual type received."""
        validator = SchemaValidator(SimpleSchema)
        result = validator.validate({"title": ["not", "a", "string"], "count": 1})

        assert result.valid is False
        error = next(e for e in result.errors if e.field == "title")
        assert "list" in error.message

    def test_nested_error_has_full_path(self) -> None:
        """Test that nested field errors include the full field path."""
        validator = SchemaValidator(NestedSchema)
        result = validator.validate({"name": "Parent", "metadata": {"count": "not-int"}})

        assert result.valid is False
        # Error should reference metadata.title (missing) or metadata.count (wrong type)
        field_paths = [e.field for e in result.errors]
        assert any("metadata." in path for path in field_paths)

    def test_unknown_field_error_includes_field_name(self) -> None:
        """Test that unknown field errors name the offending field."""
        validator = SchemaValidator(SimpleSchema, strict=True)
        result = validator.validate({"title": "Hello", "mystery_field": "value"})

        assert result.valid is False
        assert any("mystery_field" in e.field for e in result.errors)
        assert any("mystery_field" in e.message for e in result.errors)

    def test_datetime_parse_error_shows_value(self) -> None:
        """Test that datetime parse errors show the problematic value."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": "not-a-date"})

        assert result.valid is False
        error = next(e for e in result.errors if e.field == "date")
        assert "not-a-date" in error.message

    def test_list_item_error_shows_index(self) -> None:
        """Test that list item errors show the index."""
        validator = SchemaValidator(ComplexTypesSchema)
        result = validator.validate(
            {
                "items": ["valid"],
                "mapping": {},
                "optional_list": [1, 2, "not-int", 4],
            }
        )

        assert result.valid is False
        # Error should mention optional_list[2]
        assert any("optional_list[2]" in e.field for e in result.errors)


# Datetime edge case tests


class TestDatetimeEdgeCases:
    """Tests for datetime parsing edge cases."""

    def test_datetime_with_timezone(self) -> None:
        """Test datetime with timezone offset."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate(
            {
                "title": "Post",
                "date": "2025-01-15T10:30:00+05:00",
            }
        )

        assert result.valid is True
        assert result.data.date.year == 2025

    def test_datetime_iso_format_with_microseconds(self) -> None:
        """Test datetime with microseconds."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate(
            {
                "title": "Post",
                "date": "2025-01-15T10:30:00.123456",
            }
        )

        assert result.valid is True

    def test_datetime_date_only_string(self) -> None:
        """Test datetime from date-only string."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": "2025-01-15"})

        assert result.valid is True
        assert result.data.date.year == 2025
        assert result.data.date.month == 1
        assert result.data.date.day == 15

    def test_datetime_empty_string_fails(self) -> None:
        """Test that empty string fails datetime parsing."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": ""})

        assert result.valid is False

    def test_datetime_whitespace_only_fails(self) -> None:
        """Test that whitespace-only string fails datetime parsing."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": "   "})

        assert result.valid is False

    def test_datetime_from_date_object(self) -> None:
        """Test datetime field accepts date object (converts to midnight)."""
        validator = SchemaValidator(BlogPostSchema)
        result = validator.validate({"title": "Post", "date": date(2025, 1, 15)})

        assert result.valid is True
        assert isinstance(result.data.date, datetime)
        assert result.data.date.hour == 0
        assert result.data.date.minute == 0


# Date coercion edge cases


@dataclass
class DateOnlySchema:
    """Schema with date field (not datetime)."""

    published: date
    title: str = ""


class TestDateEdgeCases:
    """Tests for date parsing edge cases."""

    def test_date_from_datetime_object(self) -> None:
        """Test date field extracts date from datetime."""
        validator = SchemaValidator(DateOnlySchema)
        result = validator.validate({"published": datetime(2025, 1, 15, 10, 30)})

        assert result.valid is True
        assert result.data.published == date(2025, 1, 15)
        assert not isinstance(result.data.published, datetime)

    def test_date_from_iso_string(self) -> None:
        """Test date from ISO format string."""
        validator = SchemaValidator(DateOnlySchema)
        result = validator.validate({"published": "2025-01-15"})

        assert result.valid is True
        assert result.data.published == date(2025, 1, 15)

    def test_date_rejects_invalid_string(self) -> None:
        """Test date rejects invalid string."""
        validator = SchemaValidator(DateOnlySchema)
        result = validator.validate({"published": "not-a-date"})

        assert result.valid is False


# Pydantic integration tests (optional - only run if pydantic is installed)


class TestPydanticIntegration:
    """Tests for Pydantic model support (skipped if pydantic not installed)."""

    def test_pydantic_model_detection(self) -> None:
        """Test that Pydantic models are detected via model_validate."""
        pydantic = pytest.importorskip("pydantic")

        class PydanticSchema(pydantic.BaseModel):
            title: str
            count: int = 0

        validator = SchemaValidator(PydanticSchema)
        assert validator._is_pydantic is True

    def test_pydantic_valid_data(self) -> None:
        """Test Pydantic model validation with valid data."""
        pydantic = pytest.importorskip("pydantic")

        class PydanticSchema(pydantic.BaseModel):
            title: str
            count: int = 0

        validator = SchemaValidator(PydanticSchema)
        result = validator.validate({"title": "Hello", "count": 42})

        assert result.valid is True
        assert result.data.title == "Hello"
        assert result.data.count == 42

    def test_pydantic_missing_required(self) -> None:
        """Test Pydantic model validation with missing required field."""
        pydantic = pytest.importorskip("pydantic")

        class PydanticSchema(pydantic.BaseModel):
            title: str
            count: int = 0

        validator = SchemaValidator(PydanticSchema)
        result = validator.validate({"count": 42})

        assert result.valid is False
        assert len(result.errors) >= 1

    def test_pydantic_type_coercion(self) -> None:
        """Test Pydantic's built-in type coercion."""
        pydantic = pytest.importorskip("pydantic")

        class PydanticSchema(pydantic.BaseModel):
            count: int

        validator = SchemaValidator(PydanticSchema)
        # Pydantic should coerce "42" to 42
        result = validator.validate({"count": "42"})

        assert result.valid is True
        assert result.data.count == 42
