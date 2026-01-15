"""Tests for LocalSource."""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.content.sources.local import LocalSource, _parse_frontmatter
from bengal.errors import BengalConfigError


class TestParseFrontmatter:
    """Tests for frontmatter parsing utility."""

    def test_with_frontmatter(self) -> None:
        """Test parsing content with YAML frontmatter."""
        content = """---
title: Hello World
tags:
  - python
  - testing
---

# Content Here
"""
        frontmatter, body = _parse_frontmatter(content)

        assert frontmatter == {"title": "Hello World", "tags": ["python", "testing"]}
        assert body == "# Content Here"

    def test_without_frontmatter(self) -> None:
        """Test parsing content without frontmatter."""
        content = "# Just Content\n\nNo frontmatter here."

        frontmatter, body = _parse_frontmatter(content)

        assert frontmatter == {}
        assert body == content

    def test_empty_frontmatter(self) -> None:
        """Test parsing content with empty frontmatter."""
        content = """---
---

Body content."""

        frontmatter, body = _parse_frontmatter(content)

        assert frontmatter == {}
        assert body == "Body content."


class TestLocalSource:
    """Tests for LocalSource."""

    def test_requires_directory(self) -> None:
        """Test that LocalSource requires directory config."""
        with pytest.raises(BengalConfigError, match="requires 'directory'"):
            LocalSource("test", {})

    def test_config_parsing(self) -> None:
        """Test configuration is parsed correctly."""
        source = LocalSource(
            "docs",
            {
                "directory": "content/docs",
                "glob": "**/*.mdx",
                "exclude": ["_drafts/*"],
            },
        )

        assert source.directory == Path("content/docs")
        assert source.glob_pattern == "**/*.mdx"
        assert source.exclude_patterns == ["_drafts/*"]

    def test_default_config(self) -> None:
        """Test default configuration values."""
        source = LocalSource("test", {"directory": "content"})

        assert source.glob_pattern == "**/*.md"
        assert source.exclude_patterns == []

    def test_source_type(self) -> None:
        """Test source type is 'local'."""
        source = LocalSource("test", {"directory": "content"})
        assert source.source_type == "local"

    def test_path_to_slug(self) -> None:
        """Test path to slug conversion."""
        source = LocalSource("test", {"directory": "content"})

        # Basic file
        assert source._path_to_slug(Path("getting-started.md")) == "getting-started"

        # Nested path
        assert source._path_to_slug(Path("guides/advanced.md")) == "guides/advanced"

        # Index file
        assert source._path_to_slug(Path("index.md")) == "index"
        assert source._path_to_slug(Path("guides/index.md")) == "guides"

    def test_should_exclude(self) -> None:
        """Test exclusion pattern matching."""
        source = LocalSource(
            "test",
            {
                "directory": "content",
                "exclude": ["_drafts/*", "*.tmp"],
            },
        )

        # Excluded patterns
        assert source._should_exclude(Path("content/_drafts/post.md"))
        assert source._should_exclude(Path("content/backup.tmp"))

        # Not excluded
        assert not source._should_exclude(Path("content/posts/hello.md"))

    @pytest.mark.asyncio
    async def test_fetch_all_empty_directory(self, tmp_path: Path) -> None:
        """Test fetching from empty directory."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        source = LocalSource("test", {"directory": str(content_dir)})
        entries = [e async for e in source.fetch_all()]

        assert entries == []

    @pytest.mark.asyncio
    async def test_fetch_all_with_files(self, tmp_path: Path) -> None:
        """Test fetching files from directory."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create test files
        (content_dir / "page1.md").write_text("---\ntitle: Page 1\n---\n# Page 1")
        (content_dir / "page2.md").write_text("# Page 2 (no frontmatter)")

        source = LocalSource("docs", {"directory": str(content_dir)})
        entries = [e async for e in source.fetch_all()]

        assert len(entries) == 2

        # Check entries are populated
        slugs = {e.slug for e in entries}
        assert slugs == {"page1", "page2"}

        # Check frontmatter was parsed
        page1 = next(e for e in entries if e.slug == "page1")
        assert page1.frontmatter.get("title") == "Page 1"
        assert page1.content == "# Page 1"

    @pytest.mark.asyncio
    async def test_fetch_one(self, tmp_path: Path) -> None:
        """Test fetching single file."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "test.md").write_text("---\ntitle: Test\n---\nContent")

        source = LocalSource("test", {"directory": str(content_dir)})

        # Existing file
        entry = await source.fetch_one("test.md")
        assert entry is not None
        assert entry.slug == "test"
        assert entry.frontmatter.get("title") == "Test"

        # Non-existing file
        entry = await source.fetch_one("missing.md")
        assert entry is None

    @pytest.mark.asyncio
    async def test_fetch_one_excluded(self, tmp_path: Path) -> None:
        """Test fetch_one respects exclusion patterns."""
        content_dir = tmp_path / "content"
        drafts = content_dir / "_drafts"
        drafts.mkdir(parents=True)
        (drafts / "draft.md").write_text("Draft content")

        source = LocalSource(
            "test",
            {
                "directory": str(content_dir),
                "exclude": ["_drafts/*"],
            },
        )

        entry = await source.fetch_one("_drafts/draft.md")
        assert entry is None
