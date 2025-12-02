"""
Unit tests for CollectionConfig and define_collection.

Tests collection definition API, configuration options, and error handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pytest

from bengal.collections import CollectionConfig, define_collection


# Test schemas


@dataclass
class BlogPost:
    """Blog post schema for testing."""

    title: str
    date: datetime
    author: str = "Anonymous"
    tags: list[str] = field(default_factory=list)
    draft: bool = False


@dataclass
class DocPage:
    """Documentation page schema for testing."""

    title: str
    weight: int = 0


# define_collection tests


class TestDefineCollection:
    """Tests for define_collection function."""

    def test_basic_collection(self) -> None:
        """Test basic collection definition."""
        collection = define_collection(
            schema=BlogPost,
            directory="content/blog",
        )

        assert collection.schema is BlogPost
        assert collection.directory == Path("content/blog")
        assert collection.glob == "**/*.md"  # Default
        assert collection.strict is True  # Default

    def test_custom_glob(self) -> None:
        """Test collection with custom glob pattern."""
        collection = define_collection(
            schema=BlogPost,
            directory="content/blog",
            glob="*.md",  # Non-recursive
        )

        assert collection.glob == "*.md"

    def test_lenient_mode(self) -> None:
        """Test collection with strict=False."""
        collection = define_collection(
            schema=BlogPost,
            directory="content/blog",
            strict=False,
        )

        assert collection.strict is False

    def test_allow_extra(self) -> None:
        """Test collection with allow_extra=True."""
        collection = define_collection(
            schema=BlogPost,
            directory="content/blog",
            strict=False,
            allow_extra=True,
        )

        assert collection.allow_extra is True

    def test_with_transform(self) -> None:
        """Test collection with transform function."""

        def normalize(data: dict[str, Any]) -> dict[str, Any]:
            # Rename legacy field
            if "post_title" in data:
                data["title"] = data.pop("post_title")
            return data

        collection = define_collection(
            schema=BlogPost,
            directory="content/blog",
            transform=normalize,
        )

        assert collection.transform is normalize

    def test_directory_as_path(self) -> None:
        """Test directory can be Path object."""
        collection = define_collection(
            schema=BlogPost,
            directory=Path("content/blog"),
        )

        assert collection.directory == Path("content/blog")
        assert isinstance(collection.directory, Path)

    def test_directory_as_string(self) -> None:
        """Test directory string is converted to Path."""
        collection = define_collection(
            schema=BlogPost,
            directory="content/blog",
        )

        assert isinstance(collection.directory, Path)
        assert collection.directory == Path("content/blog")


# CollectionConfig tests


class TestCollectionConfig:
    """Tests for CollectionConfig dataclass."""

    def test_direct_instantiation(self) -> None:
        """Test direct CollectionConfig instantiation."""
        config = CollectionConfig(
            schema=BlogPost,
            directory=Path("content/blog"),
        )

        assert config.schema is BlogPost
        assert config.directory == Path("content/blog")

    def test_string_directory_converted(self) -> None:
        """Test string directory is converted in __post_init__."""
        config = CollectionConfig(
            schema=BlogPost,
            directory="content/blog",  # type: ignore
        )

        assert isinstance(config.directory, Path)

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        config = CollectionConfig(
            schema=BlogPost,
            directory=Path("content/blog"),
        )

        assert config.glob == "**/*.md"
        assert config.strict is True
        assert config.allow_extra is False
        assert config.transform is None


# Multiple collections


class TestMultipleCollections:
    """Tests for defining multiple collections."""

    def test_collections_dict(self) -> None:
        """Test typical collections dictionary pattern."""
        collections = {
            "blog": define_collection(
                schema=BlogPost,
                directory="content/blog",
            ),
            "docs": define_collection(
                schema=DocPage,
                directory="content/docs",
            ),
        }

        assert "blog" in collections
        assert "docs" in collections
        assert collections["blog"].schema is BlogPost
        assert collections["docs"].schema is DocPage

    def test_different_directories(self) -> None:
        """Test collections can have different directories."""
        collections = {
            "posts": define_collection(
                schema=BlogPost,
                directory="content/posts",
            ),
            "articles": define_collection(
                schema=BlogPost,  # Same schema, different directory
                directory="content/articles",
            ),
        }

        assert collections["posts"].directory != collections["articles"].directory

    def test_different_strictness(self) -> None:
        """Test collections can have different strictness."""
        collections = {
            "strict": define_collection(
                schema=BlogPost,
                directory="content/strict",
                strict=True,
            ),
            "lenient": define_collection(
                schema=BlogPost,
                directory="content/lenient",
                strict=False,
            ),
        }

        assert collections["strict"].strict is True
        assert collections["lenient"].strict is False


# Transform function tests


class TestTransformFunction:
    """Tests for collection transform functions."""

    def test_transform_called(self) -> None:
        """Test transform function is stored correctly."""
        call_count = {"count": 0}

        def track_calls(data: dict[str, Any]) -> dict[str, Any]:
            call_count["count"] += 1
            return data

        collection = define_collection(
            schema=BlogPost,
            directory="content/blog",
            transform=track_calls,
        )

        assert collection.transform is not None

        # Transform can be called
        result = collection.transform({"title": "test"})
        assert call_count["count"] == 1
        assert result == {"title": "test"}

    def test_transform_modifies_data(self) -> None:
        """Test transform function can modify data."""

        def add_defaults(data: dict[str, Any]) -> dict[str, Any]:
            data.setdefault("author", "Default Author")
            data.setdefault("draft", False)
            return data

        collection = define_collection(
            schema=BlogPost,
            directory="content/blog",
            transform=add_defaults,
        )

        # Apply transform
        input_data = {"title": "Test", "date": datetime.now()}
        result = collection.transform(input_data)

        assert result["author"] == "Default Author"
        assert result["draft"] is False

    def test_transform_renames_fields(self) -> None:
        """Test transform function can rename fields."""

        def migrate_legacy(data: dict[str, Any]) -> dict[str, Any]:
            # Migrate old field names to new
            if "post_title" in data:
                data["title"] = data.pop("post_title")
            if "publish_date" in data:
                data["date"] = data.pop("publish_date")
            return data

        collection = define_collection(
            schema=BlogPost,
            directory="content/blog",
            transform=migrate_legacy,
        )

        # Apply transform to legacy data
        legacy_data = {
            "post_title": "Old Title",
            "publish_date": datetime(2025, 1, 15),
        }
        result = collection.transform(legacy_data)

        assert "title" in result
        assert "date" in result
        assert "post_title" not in result
        assert "publish_date" not in result


# Generic type parameter tests


class TestGenericTypeParameter:
    """Tests for CollectionConfig generic type parameter."""

    def test_type_parameter_preserved(self) -> None:
        """Test generic type parameter is preserved."""
        collection: CollectionConfig[BlogPost] = define_collection(
            schema=BlogPost,
            directory="content/blog",
        )

        # Type checker should know collection.schema is BlogPost
        assert collection.schema.__name__ == "BlogPost"

    def test_different_type_parameters(self) -> None:
        """Test different type parameters for different collections."""
        blog: CollectionConfig[BlogPost] = define_collection(
            schema=BlogPost,
            directory="content/blog",
        )
        docs: CollectionConfig[DocPage] = define_collection(
            schema=DocPage,
            directory="content/docs",
        )

        assert blog.schema is BlogPost
        assert docs.schema is DocPage

