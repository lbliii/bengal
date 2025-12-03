"""
Unit tests for bengal.pipeline.bengal_streams - Bengal-specific stream adapters.

Tests:
    - ParsedContent dataclass
    - ContentDiscoveryStream file discovery
    - FileChangeStream for incremental builds
"""

from __future__ import annotations

from pathlib import Path

from bengal.pipeline.bengal_streams import (
    ContentDiscoveryStream,
    FileChangeStream,
    ParsedContent,
)


class TestParsedContent:
    """Tests for ParsedContent dataclass."""

    def test_creation(self, tmp_path: Path) -> None:
        """ParsedContent stores all fields."""
        file_path = tmp_path / "test.md"

        content = ParsedContent(
            source_path=file_path,
            content="# Hello",
            metadata={"title": "Test"},
            content_hash="abc123",
        )

        assert content.source_path == file_path
        assert content.content == "# Hello"
        assert content.metadata == {"title": "Test"}
        assert content.content_hash == "abc123"


class TestContentDiscoveryStream:
    """Tests for ContentDiscoveryStream."""

    def test_discovers_markdown_files(self, tmp_path: Path) -> None:
        """Stream discovers .md files."""
        # Create test content
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "page1.md").write_text("# Page 1")
        (content_dir / "page2.md").write_text("# Page 2")

        stream = ContentDiscoveryStream(content_dir)
        result = stream.materialize()

        assert len(result) == 2
        names = {p.source_path.name for p in result}
        assert names == {"page1.md", "page2.md"}

    def test_discovers_nested_files(self, tmp_path: Path) -> None:
        """Stream discovers files in subdirectories."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "page.md").write_text("# Root")

        docs = content_dir / "docs"
        docs.mkdir()
        (docs / "guide.md").write_text("# Guide")

        stream = ContentDiscoveryStream(content_dir)
        result = stream.materialize()

        assert len(result) == 2

    def test_includes_index_files(self, tmp_path: Path) -> None:
        """Stream includes _index.md files."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text("# Section Index")
        (content_dir / "page.md").write_text("# Page")

        stream = ContentDiscoveryStream(content_dir)
        result = stream.materialize()

        assert len(result) == 2
        names = {p.source_path.name for p in result}
        assert "_index.md" in names

    def test_excludes_hidden_files(self, tmp_path: Path) -> None:
        """Stream excludes hidden files by default."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "visible.md").write_text("# Visible")
        (content_dir / ".hidden.md").write_text("# Hidden")

        stream = ContentDiscoveryStream(content_dir)
        result = stream.materialize()

        assert len(result) == 1
        assert result[0].source_path.name == "visible.md"

    def test_excludes_non_markdown(self, tmp_path: Path) -> None:
        """Stream excludes non-markdown files."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "page.md").write_text("# Markdown")
        (content_dir / "image.png").write_bytes(b"PNG")
        (content_dir / "style.css").write_text("body {}")

        stream = ContentDiscoveryStream(content_dir)
        result = stream.materialize()

        assert len(result) == 1
        assert result[0].source_path.name == "page.md"

    def test_parses_frontmatter(self, tmp_path: Path) -> None:
        """Stream parses YAML frontmatter."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "post.md").write_text(
            "---\ntitle: My Post\ntags:\n  - python\n  - bengal\n---\n# Content"
        )

        stream = ContentDiscoveryStream(content_dir)
        result = stream.materialize()

        assert len(result) == 1
        assert result[0].metadata["title"] == "My Post"
        assert result[0].metadata["tags"] == ["python", "bengal"]
        assert result[0].content == "# Content"

    def test_handles_invalid_frontmatter(self, tmp_path: Path) -> None:
        """Stream handles invalid frontmatter gracefully."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        # Invalid YAML (unbalanced quotes)
        (content_dir / "bad.md").write_text('---\ntitle: "unclosed\n---\n# Content')

        stream = ContentDiscoveryStream(content_dir)
        result = stream.materialize()

        # Should still produce result with fallback metadata
        assert len(result) == 1
        assert "_parse_error" in result[0].metadata

    def test_generates_content_hash(self, tmp_path: Path) -> None:
        """Stream generates content hash for each file."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "page.md").write_text("# Same content")

        stream = ContentDiscoveryStream(content_dir)
        result = stream.materialize()

        assert len(result) == 1
        assert result[0].content_hash is not None
        assert len(result[0].content_hash) == 16

    def test_stream_item_keys(self, tmp_path: Path) -> None:
        """Stream items have proper keys."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "page.md").write_text("# Page")

        stream = ContentDiscoveryStream(content_dir)
        items = list(stream.iterate())

        assert len(items) == 1
        assert items[0].key.source == "content_discovery"
        assert items[0].key.id == "page.md"
        assert len(items[0].key.version) == 16

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Stream handles empty directory."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        stream = ContentDiscoveryStream(content_dir)
        result = stream.materialize()

        assert result == []


class TestFileChangeStream:
    """Tests for FileChangeStream."""

    def test_emits_changed_files(self, tmp_path: Path) -> None:
        """Stream emits all changed file paths."""
        files = [
            tmp_path / "page1.md",
            tmp_path / "page2.md",
        ]

        stream = FileChangeStream(files)
        result = stream.materialize()

        assert len(result) == 2
        assert set(result) == set(files)

    def test_empty_changes(self) -> None:
        """Stream handles empty change list."""
        stream = FileChangeStream([])
        result = stream.materialize()

        assert result == []

    def test_stream_item_keys(self, tmp_path: Path) -> None:
        """Stream items have proper keys."""
        file_path = tmp_path / "changed.md"

        stream = FileChangeStream([file_path])
        items = list(stream.iterate())

        assert len(items) == 1
        assert items[0].key.source == "file_changes"
        assert str(file_path) in items[0].key.id

    def test_version_uniqueness(self, tmp_path: Path) -> None:
        """Each iteration produces unique versions (timestamp-based)."""
        files = [tmp_path / "page.md"]

        stream1 = FileChangeStream(files)
        items1 = list(stream1.iterate())

        stream2 = FileChangeStream(files)
        items2 = list(stream2.iterate())

        # Versions should differ (based on timestamp)
        assert items1[0].key.version != items2[0].key.version


class TestContentDiscoveryWithPipeline:
    """Integration tests for ContentDiscoveryStream with pipeline operators."""

    def test_filter_by_path(self, tmp_path: Path) -> None:
        """Filter discovered content by path pattern."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        docs = content_dir / "docs"
        docs.mkdir()
        (docs / "guide.md").write_text("# Guide")

        blog = content_dir / "blog"
        blog.mkdir()
        (blog / "post.md").write_text("# Post")

        stream = ContentDiscoveryStream(content_dir)

        # Filter to docs only
        docs_stream = stream.filter(lambda p: "docs" in str(p.source_path))
        result = docs_stream.materialize()

        assert len(result) == 1
        assert "docs" in str(result[0].source_path)

    def test_map_to_extract_title(self, tmp_path: Path) -> None:
        """Map discovered content to extract titles."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "post.md").write_text("---\ntitle: My Post\n---\n# Content")

        stream = ContentDiscoveryStream(content_dir)
        titles = stream.map(lambda p: p.metadata.get("title", "Untitled")).materialize()

        assert titles == ["My Post"]

    def test_collect_all_content(self, tmp_path: Path) -> None:
        """Collect all discovered content."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "page1.md").write_text("# Page 1")
        (content_dir / "page2.md").write_text("# Page 2")

        stream = ContentDiscoveryStream(content_dir)
        collected = stream.collect().materialize()

        assert len(collected) == 1
        assert len(collected[0]) == 2
