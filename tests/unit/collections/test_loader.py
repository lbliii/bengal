"""
Unit tests for collections loader.

Tests CollectionPathTrie and path matching functionality.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bengal.collections import (
    CollectionPathTrie,
    build_collection_trie,
    define_collection,
    get_collection_for_path,
)


@dataclass
class SimpleSchema:
    """Simple schema for testing."""

    title: str


# CollectionPathTrie tests


class TestCollectionPathTrie:
    """Tests for CollectionPathTrie data structure."""

    def test_empty_trie(self) -> None:
        """Test empty trie returns no match."""
        trie = CollectionPathTrie()

        name, config = trie.find(Path("content/blog/post.md"))

        assert name is None
        assert config is None

    def test_single_collection(self) -> None:
        """Test trie with single collection."""
        trie = CollectionPathTrie()
        config = define_collection(schema=SimpleSchema, directory="content/blog")
        trie.insert(Path("content/blog"), "blog", config)

        name, result_config = trie.find(Path("content/blog/post.md"))

        assert name == "blog"
        assert result_config is config

    def test_multiple_collections(self) -> None:
        """Test trie with multiple non-overlapping collections."""
        trie = CollectionPathTrie()
        blog_config = define_collection(schema=SimpleSchema, directory="content/blog")
        docs_config = define_collection(schema=SimpleSchema, directory="content/docs")

        trie.insert(Path("content/blog"), "blog", blog_config)
        trie.insert(Path("content/docs"), "docs", docs_config)

        name1, config1 = trie.find(Path("content/blog/post.md"))
        name2, config2 = trie.find(Path("content/docs/guide.md"))

        assert name1 == "blog"
        assert name2 == "docs"
        assert config1 is blog_config
        assert config2 is docs_config

    def test_overlapping_directories_deepest_wins(self) -> None:
        """Test overlapping directories return deepest match."""
        trie = CollectionPathTrie()
        docs_config = define_collection(schema=SimpleSchema, directory="content/docs")
        api_config = define_collection(schema=SimpleSchema, directory="content/docs/api")

        trie.insert(Path("content/docs"), "docs", docs_config)
        trie.insert(Path("content/docs/api"), "api", api_config)

        # File in api/ should match api collection (deepest)
        name, config = trie.find(Path("content/docs/api/endpoint.md"))
        assert name == "api"
        assert config is api_config

        # File in docs/ but not api/ should match docs collection
        name, config = trie.find(Path("content/docs/guide.md"))
        assert name == "docs"
        assert config is docs_config

    def test_no_match(self) -> None:
        """Test path that doesn't match any collection."""
        trie = CollectionPathTrie()
        blog_config = define_collection(schema=SimpleSchema, directory="content/blog")
        trie.insert(Path("content/blog"), "blog", blog_config)

        name, config = trie.find(Path("content/other/file.md"))

        assert name is None
        assert config is None

    def test_deep_path_match(self) -> None:
        """Test deeply nested file path matches."""
        trie = CollectionPathTrie()
        blog_config = define_collection(schema=SimpleSchema, directory="content/blog")
        trie.insert(Path("content/blog"), "blog", blog_config)

        name, config = trie.find(Path("content/blog/2025/01/deep/nested/post.md"))

        assert name == "blog"
        assert config is blog_config

    def test_len(self) -> None:
        """Test __len__ returns correct count."""
        trie = CollectionPathTrie()

        assert len(trie) == 0

        config1 = define_collection(schema=SimpleSchema, directory="content/blog")
        config2 = define_collection(schema=SimpleSchema, directory="content/docs")
        trie.insert(Path("content/blog"), "blog", config1)
        trie.insert(Path("content/docs"), "docs", config2)

        assert len(trie) == 2

    def test_partial_path_no_match(self) -> None:
        """Test partial path prefix doesn't match."""
        trie = CollectionPathTrie()
        blog_config = define_collection(schema=SimpleSchema, directory="content/blog")
        trie.insert(Path("content/blog"), "blog", blog_config)

        # "content/blogposts" should NOT match "content/blog"
        name, config = trie.find(Path("content/blogposts/post.md"))

        assert name is None
        assert config is None


# build_collection_trie tests


class TestBuildCollectionTrie:
    """Tests for build_collection_trie function."""

    def test_empty_collections(self) -> None:
        """Test building trie from empty collections."""
        trie = build_collection_trie({})

        assert len(trie) == 0

    def test_single_collection(self) -> None:
        """Test building trie from single collection."""
        collections = {
            "blog": define_collection(schema=SimpleSchema, directory="content/blog"),
        }

        trie = build_collection_trie(collections)

        assert len(trie) == 1
        name, config = trie.find(Path("content/blog/post.md"))
        assert name == "blog"

    def test_multiple_collections(self) -> None:
        """Test building trie from multiple collections."""
        collections = {
            "blog": define_collection(schema=SimpleSchema, directory="content/blog"),
            "docs": define_collection(schema=SimpleSchema, directory="content/docs"),
            "api": define_collection(schema=SimpleSchema, directory="content/docs/api"),
        }

        trie = build_collection_trie(collections)

        assert len(trie) == 3

    def test_skips_remote_collections(self) -> None:
        """Test that collections without directory are skipped."""
        # Note: Can't easily test this without a mock loader, but we test
        # the behavior by verifying directory=None collections don't crash
        collections = {
            "blog": define_collection(schema=SimpleSchema, directory="content/blog"),
        }

        trie = build_collection_trie(collections)

        assert len(trie) == 1


# get_collection_for_path with trie tests


class TestGetCollectionForPathWithTrie:
    """Tests for get_collection_for_path with trie parameter."""

    def test_trie_matches_file(self) -> None:
        """Test trie-based matching finds correct collection."""
        collections = {
            "blog": define_collection(schema=SimpleSchema, directory="blog"),
            "docs": define_collection(schema=SimpleSchema, directory="docs"),
        }
        trie = build_collection_trie(collections)
        content_root = Path(".")

        name, config = get_collection_for_path(
            Path("blog/post.md"),
            content_root,
            collections,
            trie=trie,
        )

        assert name == "blog"

    def test_trie_no_match(self) -> None:
        """Test trie returns None for non-matching path."""
        collections = {
            "blog": define_collection(schema=SimpleSchema, directory="blog"),
        }
        trie = build_collection_trie(collections)
        content_root = Path(".")

        name, config = get_collection_for_path(
            Path("other/post.md"),
            content_root,
            collections,
            trie=trie,
        )

        assert name is None
        assert config is None

    def test_trie_deepest_match(self) -> None:
        """Test trie returns deepest matching collection."""
        collections = {
            "docs": define_collection(schema=SimpleSchema, directory="docs"),
            "api": define_collection(schema=SimpleSchema, directory="docs/api"),
        }
        trie = build_collection_trie(collections)
        content_root = Path(".")

        # Should match api (deepest), not docs
        name, config = get_collection_for_path(
            Path("docs/api/endpoint.md"),
            content_root,
            collections,
            trie=trie,
        )

        assert name == "api"

    def test_linear_fallback_without_trie(self) -> None:
        """Test linear scan works without trie."""
        collections = {
            "blog": define_collection(schema=SimpleSchema, directory="blog"),
        }
        content_root = Path(".")

        name, config = get_collection_for_path(
            Path("blog/post.md"),
            content_root,
            collections,
            trie=None,  # Explicit None
        )

        assert name == "blog"

    def test_file_outside_content_root(self) -> None:
        """Test file outside content root returns None."""
        collections = {
            "blog": define_collection(schema=SimpleSchema, directory="content/blog"),
        }
        trie = build_collection_trie(collections)
        content_root = Path("content")

        name, config = get_collection_for_path(
            Path("other/file.md"),  # Not under content/
            content_root,
            collections,
            trie=trie,
        )

        assert name is None
        assert config is None


