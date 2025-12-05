"""
Integration tests for collections with content discovery.

Tests that ContentDiscovery properly validates content against
collection schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pytest

from bengal.collections import CollectionConfig, ContentValidationError, define_collection
from bengal.discovery.content_discovery import ContentDiscovery

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


# Test fixtures


@pytest.fixture
def content_dir(tmp_path: Path) -> Path:
    """Create a test content directory structure."""
    content = tmp_path / "content"
    content.mkdir()

    # Create blog directory
    blog = content / "blog"
    blog.mkdir()

    # Create docs directory
    docs = content / "docs"
    docs.mkdir()

    return content


@pytest.fixture
def collections() -> dict[str, CollectionConfig]:
    """Create test collection configurations."""
    return {
        "blog": define_collection(
            schema=BlogPost,
            directory="blog",
        ),
        "docs": define_collection(
            schema=DocPage,
            directory="docs",
        ),
    }


# Basic integration tests


class TestCollectionValidation:
    """Test collection validation during content discovery."""

    def test_valid_blog_post(
        self, content_dir: Path, collections: dict[str, CollectionConfig]
    ) -> None:
        """Test valid blog post passes validation."""
        # Create valid blog post
        post = content_dir / "blog" / "my-post.md"
        post.write_text(
            """---
title: My First Post
date: 2025-01-15
author: John Doe
tags:
  - python
  - web
---

# Hello World

This is my first post.
"""
        )

        # Discover content
        discovery = ContentDiscovery(
            content_dir=content_dir,
            collections=collections,
            strict_validation=True,
        )
        sections, pages = discovery.discover()

        # Should succeed
        assert len(pages) == 1
        assert pages[0].title == "My First Post"
        assert len(discovery._validation_errors) == 0

    def test_valid_doc_page(
        self, content_dir: Path, collections: dict[str, CollectionConfig]
    ) -> None:
        """Test valid doc page passes validation."""
        # Create valid doc page
        doc = content_dir / "docs" / "getting-started.md"
        doc.write_text(
            """---
title: Getting Started
weight: 10
---

# Getting Started

Welcome to the docs.
"""
        )

        # Discover content
        discovery = ContentDiscovery(
            content_dir=content_dir,
            collections=collections,
            strict_validation=True,
        )
        sections, pages = discovery.discover()

        # Should succeed
        assert len(pages) == 1
        assert pages[0].title == "Getting Started"

    def test_missing_required_field_strict(
        self, content_dir: Path, collections: dict[str, CollectionConfig]
    ) -> None:
        """Test missing required field raises error in strict mode."""
        # Create blog post missing required 'date' field
        post = content_dir / "blog" / "bad-post.md"
        post.write_text(
            """---
author: John Doe
---

Missing title and date!
"""
        )

        # Discover with strict validation
        discovery = ContentDiscovery(
            content_dir=content_dir,
            collections=collections,
            strict_validation=True,
        )

        # Should raise ContentValidationError
        with pytest.raises(ContentValidationError) as exc_info:
            discovery.discover()

        # Error should mention missing fields
        error = exc_info.value
        assert "blog/bad-post.md" in str(error.path)
        assert any("title" in e.field for e in error.errors)
        assert any("date" in e.field for e in error.errors)

    def test_missing_required_field_lenient(
        self, content_dir: Path, collections: dict[str, CollectionConfig]
    ) -> None:
        """Test missing required field logs warning in lenient mode."""
        # Create blog post missing required 'date' field
        post = content_dir / "blog" / "bad-post.md"
        post.write_text(
            """---
author: John Doe
---

Missing title and date!
"""
        )

        # Discover with lenient validation
        discovery = ContentDiscovery(
            content_dir=content_dir,
            collections=collections,
            strict_validation=False,
        )

        # Should not raise
        sections, pages = discovery.discover()

        # Page should be created with original metadata
        assert len(pages) == 1

        # Validation errors should be recorded
        assert len(discovery._validation_errors) == 1
        path, collection, errors = discovery._validation_errors[0]
        assert "bad-post.md" in str(path)
        assert collection == "blog"

    def test_unknown_field_strict_mode(
        self, content_dir: Path, collections: dict[str, CollectionConfig]
    ) -> None:
        """Test unknown field rejected in strict collection."""
        # Create post with unknown field
        post = content_dir / "blog" / "extra-fields.md"
        post.write_text(
            """---
title: Post with Extra
date: 2025-01-15
unknown_field: should fail
---

Content here.
"""
        )

        # Discover with strict validation
        discovery = ContentDiscovery(
            content_dir=content_dir,
            collections=collections,
            strict_validation=True,
        )

        # Should raise
        with pytest.raises(ContentValidationError) as exc_info:
            discovery.discover()

        error = exc_info.value
        assert any("unknown_field" in e.field for e in error.errors)

    def test_type_coercion(
        self, content_dir: Path, collections: dict[str, CollectionConfig]
    ) -> None:
        """Test type coercion works (e.g., date string to datetime)."""
        # Create post with date as string
        post = content_dir / "blog" / "coerced.md"
        post.write_text(
            """---
title: Date Coercion Test
date: "2025-01-15"
draft: "true"
---

Content.
"""
        )

        discovery = ContentDiscovery(
            content_dir=content_dir,
            collections=collections,
            strict_validation=True,
        )
        sections, pages = discovery.discover()

        # Should succeed with coerced types
        assert len(pages) == 1
        # The validated metadata should have proper types
        # (actual Page object may still have string values in .metadata)

    def test_non_collection_content_not_validated(
        self, content_dir: Path, collections: dict[str, CollectionConfig]
    ) -> None:
        """Test content outside collections is not validated."""
        # Create page outside any collection
        page = content_dir / "about.md"
        page.write_text(
            """---
arbitrary: frontmatter
no_schema: here
---

About page not in any collection.
"""
        )

        discovery = ContentDiscovery(
            content_dir=content_dir,
            collections=collections,
            strict_validation=True,
        )
        sections, pages = discovery.discover()

        # Should succeed - no validation applied
        assert len(pages) == 1
        assert pages[0].metadata.get("arbitrary") == "frontmatter"


class TestCollectionDefaults:
    """Test that collection schemas apply default values."""

    def test_defaults_applied(
        self, content_dir: Path, collections: dict[str, CollectionConfig]
    ) -> None:
        """Test schema defaults are applied to validated content."""
        # Create minimal post (only required fields)
        post = content_dir / "blog" / "minimal.md"
        post.write_text(
            """---
title: Minimal Post
date: 2025-01-15
---

Just title and date.
"""
        )

        discovery = ContentDiscovery(
            content_dir=content_dir,
            collections=collections,
            strict_validation=True,
        )
        sections, pages = discovery.discover()

        assert len(pages) == 1
        # Defaults should be applied
        assert pages[0].metadata.get("author") == "Anonymous"
        assert pages[0].metadata.get("tags") == []
        assert pages[0].metadata.get("draft") is False


class TestCollectionTransform:
    """Test collection transform functions."""

    def test_transform_applied(self, content_dir: Path) -> None:
        """Test transform function is called before validation."""

        def normalize_legacy(data: dict) -> dict:
            # Rename old field names
            if "post_title" in data:
                data["title"] = data.pop("post_title")
            if "publish_date" in data:
                data["date"] = data.pop("publish_date")
            return data

        collections = {
            "blog": define_collection(
                schema=BlogPost,
                directory="blog",
                transform=normalize_legacy,
            ),
        }

        # Create blog directory
        blog = content_dir / "blog"
        blog.mkdir(exist_ok=True)

        # Create post with legacy field names
        post = blog / "legacy-post.md"
        post.write_text(
            """---
post_title: Legacy Title
publish_date: 2025-01-15
---

Legacy format content.
"""
        )

        discovery = ContentDiscovery(
            content_dir=content_dir,
            collections=collections,
            strict_validation=True,
        )
        sections, pages = discovery.discover()

        # Should succeed after transform
        assert len(pages) == 1
        assert pages[0].metadata.get("title") == "Legacy Title"


class TestNoCollections:
    """Test behavior when no collections are defined."""

    def test_no_collections_skips_validation(self, content_dir: Path) -> None:
        """Test that validation is skipped when no collections defined."""
        # Create any content
        page = content_dir / "anything.md"
        page.write_text(
            """---
any: frontmatter
is: fine
---

Content.
"""
        )

        # No collections
        discovery = ContentDiscovery(
            content_dir=content_dir,
            collections=None,
            strict_validation=True,
        )
        sections, pages = discovery.discover()

        # Should succeed - no validation
        assert len(pages) == 1

    def test_empty_collections_skips_validation(self, content_dir: Path) -> None:
        """Test that validation is skipped when collections dict is empty."""
        page = content_dir / "anything.md"
        page.write_text(
            """---
any: frontmatter
---

Content.
"""
        )

        discovery = ContentDiscovery(
            content_dir=content_dir,
            collections={},
            strict_validation=True,
        )
        sections, pages = discovery.discover()

        assert len(pages) == 1


class TestMultipleCollections:
    """Test with multiple collections."""

    def test_correct_collection_matched(
        self, content_dir: Path, collections: dict[str, CollectionConfig]
    ) -> None:
        """Test files are matched to correct collections."""
        # Create valid blog post
        blog_post = content_dir / "blog" / "post.md"
        blog_post.write_text(
            """---
title: Blog Post
date: 2025-01-15
---

Blog content.
"""
        )

        # Create valid doc page
        doc_page = content_dir / "docs" / "guide.md"
        doc_page.write_text(
            """---
title: Doc Guide
weight: 5
---

Doc content.
"""
        )

        discovery = ContentDiscovery(
            content_dir=content_dir,
            collections=collections,
            strict_validation=True,
        )
        sections, pages = discovery.discover()

        # Both should be validated against their respective schemas
        assert len(pages) == 2
        assert len(discovery._validation_errors) == 0

    def test_one_invalid_doesnt_affect_other(
        self, content_dir: Path, collections: dict[str, CollectionConfig]
    ) -> None:
        """Test invalid file in one collection doesn't affect valid files in lenient mode."""
        # Create invalid blog post
        bad_post = content_dir / "blog" / "bad.md"
        bad_post.write_text(
            """---
missing: required fields
---

Bad blog.
"""
        )

        # Create valid doc page
        doc_page = content_dir / "docs" / "guide.md"
        doc_page.write_text(
            """---
title: Doc Guide
---

Doc content.
"""
        )

        discovery = ContentDiscovery(
            content_dir=content_dir,
            collections=collections,
            strict_validation=False,  # Lenient mode
        )
        sections, pages = discovery.discover()

        # Both pages created
        assert len(pages) == 2
        # One validation error
        assert len(discovery._validation_errors) == 1
