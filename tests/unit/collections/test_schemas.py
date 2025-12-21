"""
Unit tests for standard collection schemas.

Tests that built-in schemas work correctly with the validator.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime

from bengal.collections import APIReference, BlogPost, Changelog, DocPage, Tutorial
from bengal.collections.validator import SchemaValidator


class TestBlogPostSchema:
    """Tests for BlogPost standard schema."""

    def test_is_dataclass(self) -> None:
        """Test BlogPost is a valid dataclass."""
        assert is_dataclass(BlogPost)

    def test_required_fields(self) -> None:
        """Test BlogPost has expected required fields."""
        schema_fields = {f.name for f in fields(BlogPost)}
        assert "title" in schema_fields
        assert "date" in schema_fields

    def test_optional_fields_have_defaults(self) -> None:
        """Test optional fields have default values."""
        # Can create with just required fields
        post = BlogPost(title="Test", date=datetime.now())
        assert post.author == "Anonymous"
        assert post.tags == []
        assert post.draft is False
        assert post.description is None

    def test_validates_minimal_frontmatter(self) -> None:
        """Test validation of minimal blog post frontmatter."""
        validator = SchemaValidator(BlogPost)
        result = validator.validate(
            {
                "title": "My Post",
                "date": "2025-01-15",
            }
        )

        assert result.valid is True
        assert result.data.title == "My Post"
        assert result.data.author == "Anonymous"

    def test_validates_full_frontmatter(self) -> None:
        """Test validation of complete blog post frontmatter."""
        validator = SchemaValidator(BlogPost)
        result = validator.validate(
            {
                "title": "My Post",
                "date": "2025-01-15",
                "author": "Jane Doe",
                "tags": ["python", "tutorial"],
                "draft": True,
                "description": "A great post",
                "image": "/images/post.jpg",
                "excerpt": "This is the excerpt...",
            }
        )

        assert result.valid is True
        assert result.data.author == "Jane Doe"
        assert result.data.tags == ["python", "tutorial"]
        assert result.data.draft is True

    def test_rejects_missing_required(self) -> None:
        """Test validation fails for missing required fields."""
        validator = SchemaValidator(BlogPost)
        result = validator.validate({"author": "John"})

        assert result.valid is False
        missing_fields = {e.field for e in result.errors}
        assert "title" in missing_fields
        assert "date" in missing_fields


class TestDocPageSchema:
    """Tests for DocPage standard schema."""

    def test_is_dataclass(self) -> None:
        """Test DocPage is a valid dataclass."""
        assert is_dataclass(DocPage)

    def test_minimal_doc_page(self) -> None:
        """Test minimal doc page with just title."""
        validator = SchemaValidator(DocPage)
        result = validator.validate({"title": "Getting Started"})

        assert result.valid is True
        assert result.data.title == "Getting Started"
        assert result.data.weight == 0
        assert result.data.toc is True

    def test_full_doc_page(self) -> None:
        """Test doc page with all fields."""
        validator = SchemaValidator(DocPage)
        result = validator.validate(
            {
                "title": "API Reference",
                "weight": 100,
                "category": "Reference",
                "tags": ["api", "reference"],
                "toc": False,
                "description": "Complete API docs",
                "deprecated": True,
                "since": "1.0.0",
            }
        )

        assert result.valid is True
        assert result.data.weight == 100
        assert result.data.category == "Reference"
        assert result.data.deprecated is True


class TestAPIReferenceSchema:
    """Tests for APIReference standard schema."""

    def test_is_dataclass(self) -> None:
        """Test APIReference is a valid dataclass."""
        assert is_dataclass(APIReference)

    def test_minimal_api_reference(self) -> None:
        """Test minimal API reference."""
        validator = SchemaValidator(APIReference)
        result = validator.validate(
            {
                "title": "List Users",
                "endpoint": "/api/v1/users",
            }
        )

        assert result.valid is True
        assert result.data.method == "GET"
        assert result.data.version == "v1"
        assert result.data.auth_required is True

    def test_full_api_reference(self) -> None:
        """Test API reference with all fields."""
        validator = SchemaValidator(APIReference)
        result = validator.validate(
            {
                "title": "Create User",
                "endpoint": "/api/v1/users",
                "method": "POST",
                "version": "v2",
                "deprecated": True,
                "auth_required": True,
                "rate_limit": "100 req/min",
                "description": "Creates a new user",
            }
        )

        assert result.valid is True
        assert result.data.method == "POST"
        assert result.data.deprecated is True


class TestTutorialSchema:
    """Tests for Tutorial standard schema."""

    def test_is_dataclass(self) -> None:
        """Test Tutorial is a valid dataclass."""
        assert is_dataclass(Tutorial)

    def test_minimal_tutorial(self) -> None:
        """Test minimal tutorial."""
        validator = SchemaValidator(Tutorial)
        result = validator.validate({"title": "Getting Started"})

        assert result.valid is True
        assert result.data.difficulty is None
        assert result.data.prerequisites == []

    def test_full_tutorial(self) -> None:
        """Test tutorial with all fields."""
        validator = SchemaValidator(Tutorial)
        result = validator.validate(
            {
                "title": "Advanced Patterns",
                "difficulty": "advanced",
                "duration": "45 minutes",
                "prerequisites": ["Basic Python", "OOP concepts"],
                "tags": ["advanced", "patterns"],
                "series": "Python Mastery",
                "order": 3,
            }
        )

        assert result.valid is True
        assert result.data.difficulty == "advanced"
        assert len(result.data.prerequisites) == 2
        assert result.data.order == 3


class TestChangelogSchema:
    """Tests for Changelog standard schema."""

    def test_is_dataclass(self) -> None:
        """Test Changelog is a valid dataclass."""
        assert is_dataclass(Changelog)

    def test_minimal_changelog(self) -> None:
        """Test minimal changelog entry."""
        validator = SchemaValidator(Changelog)
        result = validator.validate(
            {
                "title": "v1.0.0",
                "date": "2025-01-15",
            }
        )

        assert result.valid is True
        assert result.data.breaking is False
        assert result.data.draft is False

    def test_full_changelog(self) -> None:
        """Test changelog with all fields."""
        validator = SchemaValidator(Changelog)
        result = validator.validate(
            {
                "title": "Version 2.0.0",
                "date": "2025-01-15",
                "version": "2.0.0",
                "breaking": True,
                "draft": False,
                "summary": "Major release with breaking changes",
            }
        )

        assert result.valid is True
        assert result.data.breaking is True
        assert result.data.version == "2.0.0"


class TestSchemaAliases:
    """Tests for schema aliases."""

    def test_post_alias(self) -> None:
        """Test Post is alias for BlogPost."""
        from bengal.collections import Post

        assert Post is BlogPost

    def test_doc_alias(self) -> None:
        """Test Doc is alias for DocPage."""
        from bengal.collections import Doc

        assert Doc is DocPage

    def test_api_alias(self) -> None:
        """Test API is alias for APIReference."""
        from bengal.collections import API

        assert API is APIReference
