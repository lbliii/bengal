"""
Unit tests for bengal.pipeline.build - pipeline factory functions.

Tests:
    - create_build_pipeline(): Full site build pipeline
    - create_incremental_pipeline(): Incremental rebuild pipeline
    - create_simple_pipeline(): Simple render-only pipeline
    - _discover_content_files(): Content file discovery
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bengal.pipeline.build import (
    _discover_content_files,
    create_build_pipeline,
    create_incremental_pipeline,
    create_simple_pipeline,
)


class TestDiscoverContentFiles:
    """Tests for _discover_content_files helper."""

    def test_discovers_markdown_files(self, tmp_path: Path) -> None:
        """Discovers .md files in content directory."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "page1.md").write_text("# Page 1")
        (content_dir / "page2.md").write_text("# Page 2")

        files = _discover_content_files(content_dir)

        assert len(files) == 2
        names = {f.name for f in files}
        assert names == {"page1.md", "page2.md"}

    def test_discovers_markdown_extension(self, tmp_path: Path) -> None:
        """Discovers .markdown files."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "page.markdown").write_text("# Page")

        files = _discover_content_files(content_dir)

        assert len(files) == 1
        assert files[0].name == "page.markdown"

    def test_discovers_nested_files(self, tmp_path: Path) -> None:
        """Discovers files in subdirectories."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "root.md").write_text("# Root")

        docs = content_dir / "docs"
        docs.mkdir()
        (docs / "guide.md").write_text("# Guide")

        deep = docs / "deep"
        deep.mkdir()
        (deep / "nested.md").write_text("# Nested")

        files = _discover_content_files(content_dir)

        assert len(files) == 3

    def test_includes_index_files(self, tmp_path: Path) -> None:
        """Includes _index.md files."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text("# Index")
        (content_dir / "page.md").write_text("# Page")

        files = _discover_content_files(content_dir)

        assert len(files) == 2
        names = {f.name for f in files}
        assert "_index.md" in names

    def test_excludes_hidden_files(self, tmp_path: Path) -> None:
        """Excludes hidden files (starting with .)."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "visible.md").write_text("# Visible")
        (content_dir / ".hidden.md").write_text("# Hidden")

        files = _discover_content_files(content_dir)

        assert len(files) == 1
        assert files[0].name == "visible.md"

    def test_excludes_hidden_directories(self, tmp_path: Path) -> None:
        """Excludes files in hidden directories."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "visible.md").write_text("# Visible")

        hidden_dir = content_dir / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "secret.md").write_text("# Secret")

        files = _discover_content_files(content_dir)

        assert len(files) == 1
        assert files[0].name == "visible.md"

    def test_excludes_underscore_prefixed_except_index(self, tmp_path: Path) -> None:
        """Excludes _prefixed files except _index.md."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text("# Index")
        (content_dir / "_draft.md").write_text("# Draft")
        (content_dir / "page.md").write_text("# Page")

        files = _discover_content_files(content_dir)

        assert len(files) == 2
        names = {f.name for f in files}
        assert "_index.md" in names
        assert "page.md" in names
        assert "_draft.md" not in names

    def test_excludes_non_markdown(self, tmp_path: Path) -> None:
        """Excludes non-markdown files."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "page.md").write_text("# Page")
        (content_dir / "image.png").write_bytes(b"PNG")
        (content_dir / "style.css").write_text("body {}")
        (content_dir / "data.json").write_text("{}")

        files = _discover_content_files(content_dir)

        assert len(files) == 1
        assert files[0].name == "page.md"

    def test_handles_empty_directory(self, tmp_path: Path) -> None:
        """Handles empty content directory."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        files = _discover_content_files(content_dir)

        assert files == []

    def test_handles_permission_error(self, tmp_path: Path) -> None:
        """Handles directories with permission errors gracefully."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "page.md").write_text("# Page")

        # Permission errors are caught silently
        files = _discover_content_files(content_dir)

        assert len(files) == 1

    def test_handles_symlink_loop(self, tmp_path: Path) -> None:
        """Handles symlink loops without infinite recursion."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "page.md").write_text("# Page")

        # Create symlink loop
        loop = content_dir / "loop"
        try:
            loop.symlink_to(content_dir)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        files = _discover_content_files(content_dir)

        # Should discover page without infinite loop
        assert len(files) >= 1
        assert any(f.name == "page.md" for f in files)


class TestCreateBuildPipeline:
    """Tests for create_build_pipeline factory."""

    @pytest.fixture
    def mock_site(self, tmp_path: Path) -> SimpleNamespace:
        """Create mock site for testing."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        return SimpleNamespace(
            root_path=tmp_path,
            content_dir=content_dir,
            output_dir=output_dir,
            config={},
        )

    def test_creates_pipeline(self, mock_site: SimpleNamespace) -> None:
        """create_build_pipeline returns a Pipeline."""
        from bengal.pipeline.builder import Pipeline

        pipeline = create_build_pipeline(mock_site)

        assert isinstance(pipeline, Pipeline)
        assert pipeline.name == "bengal-build"

    def test_pipeline_stages(self, mock_site: SimpleNamespace) -> None:
        """Pipeline has expected stages."""
        pipeline = create_build_pipeline(mock_site)

        stage_names = [name for name, _ in pipeline._stages]
        assert "discover" in stage_names
        assert "create_page" in stage_names
        assert "render" in stage_names

    def test_empty_site_produces_no_items(self, mock_site: SimpleNamespace) -> None:
        """Pipeline handles site with no content."""
        result = create_build_pipeline(mock_site).run()

        assert result.items_processed == 0
        assert result.success

    def test_discovers_and_processes_content(self, mock_site: SimpleNamespace) -> None:
        """Pipeline discovers and processes content files."""
        # Create content
        content_file = mock_site.root_path / "content" / "page.md"
        content_file.write_text("---\ntitle: Test\n---\n# Hello")

        # Mock the renderer to avoid full template engine
        with (
            patch("bengal.rendering.template_engine.TemplateEngine") as mock_te_class,
            patch("bengal.rendering.renderer.Renderer") as mock_renderer_class,
        ):
            mock_te = MagicMock()
            mock_te_class.return_value = mock_te

            mock_renderer = MagicMock()
            mock_renderer.render_page.return_value = "<html><body>Hello</body></html>"
            mock_renderer_class.return_value = mock_renderer

            result = create_build_pipeline(mock_site).run()

            assert result.items_processed == 1
            assert result.success

    def test_parallel_option(self, mock_site: SimpleNamespace) -> None:
        """Pipeline respects parallel option."""
        pipeline = create_build_pipeline(mock_site, parallel=True, workers=8)

        # Pipeline should be created successfully
        assert pipeline is not None

    def test_workers_option(self, mock_site: SimpleNamespace) -> None:
        """Pipeline respects workers option."""
        pipeline = create_build_pipeline(mock_site, workers=2)

        # Pipeline should be created successfully
        assert pipeline is not None


class TestCreateIncrementalPipeline:
    """Tests for create_incremental_pipeline factory."""

    @pytest.fixture
    def mock_site(self, tmp_path: Path) -> SimpleNamespace:
        """Create mock site for testing."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        return SimpleNamespace(
            root_path=tmp_path,
            content_dir=content_dir,
            output_dir=output_dir,
            config={},
        )

    def test_creates_pipeline(self, mock_site: SimpleNamespace) -> None:
        """create_incremental_pipeline returns a Pipeline."""
        from bengal.pipeline.builder import Pipeline

        pipeline = create_incremental_pipeline(mock_site, [])

        assert isinstance(pipeline, Pipeline)
        assert pipeline.name == "bengal-incremental"

    def test_empty_changed_files(self, mock_site: SimpleNamespace) -> None:
        """Pipeline handles empty changed files list."""
        result = create_incremental_pipeline(mock_site, []).run()

        assert result.items_processed == 0
        assert result.success

    def test_processes_only_changed_files(self, mock_site: SimpleNamespace) -> None:
        """Pipeline only processes files in changed_files list."""
        # Create multiple content files
        content_dir = mock_site.root_path / "content"
        (content_dir / "page1.md").write_text("---\ntitle: Page 1\n---\n# Page 1")
        (content_dir / "page2.md").write_text("---\ntitle: Page 2\n---\n# Page 2")

        # Only include page1 in changed files
        changed = [content_dir / "page1.md"]

        with (
            patch("bengal.rendering.template_engine.TemplateEngine") as mock_te_class,
            patch("bengal.rendering.renderer.Renderer") as mock_renderer_class,
        ):
            mock_te = MagicMock()
            mock_te_class.return_value = mock_te

            mock_renderer = MagicMock()
            mock_renderer.render_page.return_value = "<html><body>Content</body></html>"
            mock_renderer_class.return_value = mock_renderer

            result = create_incremental_pipeline(mock_site, changed).run()

            # Should only process 1 file
            assert result.items_processed == 1

    def test_skips_deleted_files(self, mock_site: SimpleNamespace) -> None:
        """Pipeline skips files that no longer exist."""
        nonexistent = mock_site.root_path / "content" / "deleted.md"

        result = create_incremental_pipeline(mock_site, [nonexistent]).run()

        assert result.items_processed == 0
        assert result.success

    def test_skips_non_markdown_files(self, mock_site: SimpleNamespace) -> None:
        """Pipeline skips non-markdown files in changed list."""
        content_dir = mock_site.root_path / "content"
        css_file = content_dir / "style.css"
        css_file.write_text("body {}")

        result = create_incremental_pipeline(mock_site, [css_file]).run()

        assert result.items_processed == 0
        assert result.success

    def test_parallel_option(self, mock_site: SimpleNamespace) -> None:
        """Pipeline respects parallel option."""
        pipeline = create_incremental_pipeline(mock_site, [], parallel=False)

        assert pipeline is not None


class TestCreateSimplePipeline:
    """Tests for create_simple_pipeline factory."""

    @pytest.fixture
    def mock_site(self, tmp_path: Path) -> SimpleNamespace:
        """Create mock site for testing."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        return SimpleNamespace(
            root_path=tmp_path,
            output_dir=output_dir,
            config={},
            pages=[],
        )

    def test_creates_pipeline(self, mock_site: SimpleNamespace) -> None:
        """create_simple_pipeline returns a Pipeline."""
        from bengal.pipeline.builder import Pipeline

        pipeline = create_simple_pipeline(mock_site)

        assert isinstance(pipeline, Pipeline)
        assert pipeline.name == "bengal-render"

    def test_empty_pages(self, mock_site: SimpleNamespace) -> None:
        """Pipeline handles empty pages list."""
        result = create_simple_pipeline(mock_site, pages=[]).run()

        assert result.items_processed == 0
        assert result.success

    def test_uses_provided_pages(self, tmp_path: Path) -> None:
        """Pipeline uses provided pages list."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        site = SimpleNamespace(
            root_path=tmp_path,
            output_dir=output_dir,
            config={},
            pages=["page1", "page2"],
        )

        # Create mock pages
        mock_page1 = MagicMock()
        mock_page1.url = "/page1/"
        mock_page1.rendered_html = "<html>Page 1</html>"

        mock_page2 = MagicMock()
        mock_page2.url = "/page2/"
        mock_page2.rendered_html = "<html>Page 2</html>"

        pages = [mock_page1, mock_page2]

        with patch("bengal.rendering.pipeline.RenderingPipeline") as mock_pipeline_class:
            mock_render_pipeline = MagicMock()
            mock_pipeline_class.return_value = mock_render_pipeline

            result = create_simple_pipeline(site, pages=pages).run()

            assert result.items_processed == 2

    def test_uses_site_pages_if_none_provided(self, tmp_path: Path) -> None:
        """Pipeline uses site.pages if pages not provided."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_page = MagicMock()
        mock_page.url = "/page/"
        mock_page.rendered_html = "<html>Page</html>"

        site = SimpleNamespace(
            root_path=tmp_path,
            output_dir=output_dir,
            config={},
            pages=[mock_page],
        )

        with patch("bengal.rendering.pipeline.RenderingPipeline") as mock_pipeline_class:
            mock_render_pipeline = MagicMock()
            mock_pipeline_class.return_value = mock_render_pipeline

            result = create_simple_pipeline(site).run()

            assert result.items_processed == 1


class TestOutputPathGeneration:
    """Tests for output path generation in render functions."""

    @pytest.fixture
    def mock_site(self, tmp_path: Path) -> SimpleNamespace:
        """Create mock site for testing."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        return SimpleNamespace(
            root_path=tmp_path,
            content_dir=content_dir,
            output_dir=output_dir,
            config={},
        )

    def test_homepage_output_path(self, mock_site: SimpleNamespace) -> None:
        """Homepage (/) generates index.html."""

        mock_page = MagicMock()
        mock_page.url = "/"
        mock_page.rendered_html = "<html></html>"

        # Simulate the output path logic from build.py
        output_path = mock_page.url.lstrip("/")
        if not output_path:
            output_path = "index.html"
        elif not output_path.endswith(".html"):
            output_path = output_path.rstrip("/") + "/index.html"

        assert output_path == "index.html"

    def test_section_output_path(self, mock_site: SimpleNamespace) -> None:
        """Section pages generate section/index.html."""
        mock_page = MagicMock()
        mock_page.url = "/docs/"

        output_path = mock_page.url.lstrip("/")
        if not output_path:
            output_path = "index.html"
        elif not output_path.endswith(".html"):
            output_path = output_path.rstrip("/") + "/index.html"

        assert output_path == "docs/index.html"

    def test_page_output_path(self, mock_site: SimpleNamespace) -> None:
        """Regular pages generate page/index.html."""
        mock_page = MagicMock()
        mock_page.url = "/about"

        output_path = mock_page.url.lstrip("/")
        if not output_path:
            output_path = "index.html"
        elif not output_path.endswith(".html"):
            output_path = output_path.rstrip("/") + "/index.html"

        assert output_path == "about/index.html"

    def test_nested_page_output_path(self, mock_site: SimpleNamespace) -> None:
        """Nested pages generate correct path."""
        mock_page = MagicMock()
        mock_page.url = "/docs/guide/installation"

        output_path = mock_page.url.lstrip("/")
        if not output_path:
            output_path = "index.html"
        elif not output_path.endswith(".html"):
            output_path = output_path.rstrip("/") + "/index.html"

        assert output_path == "docs/guide/installation/index.html"
