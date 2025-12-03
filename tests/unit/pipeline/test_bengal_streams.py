"""
Unit tests for bengal.pipeline.bengal_streams - Bengal-specific stream adapters.

Tests:
    - ParsedContent dataclass
    - ContentDiscoveryStream file discovery
    - FileChangeStream for incremental builds
    - RenderedPage dataclass
    - Factory functions: create_content_stream, create_page_stream, create_render_stream
    - write_output utility
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bengal.pipeline.bengal_streams import (
    ContentDiscoveryStream,
    FileChangeStream,
    ParsedContent,
    RenderedPage,
    create_content_stream,
    create_page_stream,
    create_render_stream,
    write_output,
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


class TestRenderedPage:
    """Tests for RenderedPage dataclass."""

    def test_creation(self, tmp_path: Path) -> None:
        """RenderedPage stores all fields."""
        mock_page = MagicMock()
        mock_page.source_path = tmp_path / "test.md"

        rendered = RenderedPage(
            page=mock_page,
            html="<html><body>Hello</body></html>",
            output_path=Path("test/index.html"),
        )

        assert rendered.page is mock_page
        assert rendered.html == "<html><body>Hello</body></html>"
        assert rendered.output_path == Path("test/index.html")

    def test_output_path_is_relative(self) -> None:
        """output_path should be relative for joining with output_dir."""
        mock_page = MagicMock()
        rendered = RenderedPage(
            page=mock_page,
            html="<html></html>",
            output_path=Path("docs/guide/index.html"),
        )

        assert not rendered.output_path.is_absolute()
        assert rendered.output_path.parts == ("docs", "guide", "index.html")


class TestCreateContentStream:
    """Tests for create_content_stream factory."""

    def test_creates_content_discovery_stream(self, tmp_path: Path) -> None:
        """Factory creates ContentDiscoveryStream."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "page.md").write_text("# Page")

        site = SimpleNamespace(root_path=tmp_path)

        stream = create_content_stream(site)

        assert isinstance(stream, ContentDiscoveryStream)
        result = stream.materialize()
        assert len(result) == 1

    def test_uses_site_content_dir(self, tmp_path: Path) -> None:
        """Factory uses site's content directory."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "test.md").write_text("# Test")

        site = SimpleNamespace(root_path=tmp_path)

        stream = create_content_stream(site)
        result = stream.materialize()

        assert len(result) == 1
        assert result[0].source_path == content_dir / "test.md"


class TestCreatePageStream:
    """Tests for create_page_stream factory."""

    def test_creates_page_from_parsed_content(self, tmp_path: Path) -> None:
        """Factory creates Page objects from ParsedContent."""
        from bengal.pipeline.core import StreamItem
        from bengal.pipeline.streams import SourceStream

        # Create mock site
        site = SimpleNamespace(root_path=tmp_path)

        # Create ParsedContent
        parsed = ParsedContent(
            source_path=tmp_path / "test.md",
            content="# Hello World",
            metadata={"title": "Test"},
            content_hash="abc123",
        )

        # Create a source stream with ParsedContent
        items = [StreamItem.create("test", "page.md", parsed)]
        content_stream = SourceStream(lambda: iter(items), name="test")

        # Mock the Page class to avoid full initialization
        with patch("bengal.core.page.Page") as mock_page_class:
            mock_page = MagicMock()
            mock_page_class.return_value = mock_page

            page_stream = create_page_stream(content_stream, site)
            result = page_stream.materialize()

            assert len(result) == 1
            # Verify Page was called with correct args
            mock_page_class.assert_called_once_with(
                source_path=parsed.source_path,
                content=parsed.content,
                metadata=parsed.metadata,
                _site=site,
            )


class TestCreateRenderStream:
    """Tests for create_render_stream factory."""

    def test_renders_pages_to_html(self, tmp_path: Path) -> None:
        """Factory renders Page objects to HTML."""
        from bengal.pipeline.core import StreamItem
        from bengal.pipeline.streams import SourceStream

        site = SimpleNamespace(root_path=tmp_path, output_dir=tmp_path / "public")

        # Create mock page
        mock_page = MagicMock()
        mock_page.url = "/test/"
        mock_page.source_path = tmp_path / "test.md"

        items = [StreamItem.create("pages", "test.md", mock_page)]
        page_stream = SourceStream(lambda: iter(items), name="pages")

        with (
            patch("bengal.rendering.template_engine.TemplateEngine"),
            patch("bengal.rendering.renderer.Renderer") as mock_renderer_class,
        ):
            mock_renderer = MagicMock()
            mock_renderer.render_page.return_value = "<html><body>Rendered</body></html>"
            mock_renderer_class.return_value = mock_renderer

            render_stream = create_render_stream(page_stream, site)
            result = render_stream.materialize()

            assert len(result) == 1
            assert isinstance(result[0], RenderedPage)
            assert result[0].html == "<html><body>Rendered</body></html>"
            assert result[0].output_path == Path("test/index.html")

    def test_homepage_output_path(self, tmp_path: Path) -> None:
        """Homepage renders to index.html."""
        from bengal.pipeline.core import StreamItem
        from bengal.pipeline.streams import SourceStream

        site = SimpleNamespace(root_path=tmp_path, output_dir=tmp_path / "public")

        mock_page = MagicMock()
        mock_page.url = "/"
        mock_page.source_path = tmp_path / "_index.md"

        items = [StreamItem.create("pages", "_index.md", mock_page)]
        page_stream = SourceStream(lambda: iter(items), name="pages")

        with (
            patch("bengal.rendering.template_engine.TemplateEngine"),
            patch("bengal.rendering.renderer.Renderer") as mock_renderer_class,
        ):
            mock_renderer = MagicMock()
            mock_renderer.render_page.return_value = "<html></html>"
            mock_renderer_class.return_value = mock_renderer

            render_stream = create_render_stream(page_stream, site)
            result = render_stream.materialize()

            assert result[0].output_path == Path("index.html")


class TestWriteOutput:
    """Tests for write_output utility function."""

    def test_writes_file_to_disk(self, tmp_path: Path) -> None:
        """write_output writes HTML to correct location."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        site = SimpleNamespace(output_dir=output_dir)

        mock_page = MagicMock()
        rendered = RenderedPage(
            page=mock_page,
            html="<html><body>Content</body></html>",
            output_path=Path("test/index.html"),
        )

        write_output(site, rendered)

        output_file = output_dir / "test" / "index.html"
        assert output_file.exists()
        assert output_file.read_text() == "<html><body>Content</body></html>"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """write_output creates parent directories as needed."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        site = SimpleNamespace(output_dir=output_dir)

        mock_page = MagicMock()
        rendered = RenderedPage(
            page=mock_page,
            html="<html></html>",
            output_path=Path("deep/nested/path/index.html"),
        )

        write_output(site, rendered)

        output_file = output_dir / "deep" / "nested" / "path" / "index.html"
        assert output_file.exists()

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        """write_output overwrites existing files."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        # Create existing file
        existing = output_dir / "test" / "index.html"
        existing.parent.mkdir(parents=True)
        existing.write_text("Old content")

        site = SimpleNamespace(output_dir=output_dir)

        mock_page = MagicMock()
        rendered = RenderedPage(
            page=mock_page,
            html="New content",
            output_path=Path("test/index.html"),
        )

        write_output(site, rendered)

        assert existing.read_text() == "New content"

    def test_writes_utf8_content(self, tmp_path: Path) -> None:
        """write_output handles UTF-8 content correctly."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        site = SimpleNamespace(output_dir=output_dir)

        mock_page = MagicMock()
        rendered = RenderedPage(
            page=mock_page,
            html="<html><body>日本語 🎉 émoji</body></html>",
            output_path=Path("test/index.html"),
        )

        write_output(site, rendered)

        output_file = output_dir / "test" / "index.html"
        content = output_file.read_text(encoding="utf-8")
        assert "日本語" in content
        assert "🎉" in content
        assert "émoji" in content
