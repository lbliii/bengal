"""Tests for ReactiveContentHandler."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.server.reactive import ReactiveContentHandler


class TestReactiveContentHandler:
    """Tests for ReactiveContentHandler."""

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create a mock site with pages."""
        site = MagicMock()
        site.output_dir = Path("/test/site/public")
        site.pages = []
        return site

    def test_handle_content_change_page_not_found(
        self, mock_site: MagicMock, tmp_path: Path
    ) -> None:
        """Test that handle_content_change returns None when page not found."""
        mock_site.pages = []
        md_file = tmp_path / "content" / "missing.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("---\ntitle: Test\n---\nBody")

        handler = ReactiveContentHandler(mock_site, mock_site.output_dir)
        result = handler.handle_content_change(md_file)

        assert result is None

    def test_handle_content_change_read_failure(self, mock_site: MagicMock, tmp_path: Path) -> None:
        """Test that handle_content_change returns None when file cannot be read."""
        page = MagicMock()
        page.source_path = tmp_path / "content" / "page.md"
        page._raw_content = "old"
        page.html_content = "<p>old</p>"
        page.output_path = tmp_path / "public" / "page" / "index.html"
        mock_site.pages = [page]

        # Path that doesn't exist
        handler = ReactiveContentHandler(mock_site, mock_site.output_dir)
        result = handler.handle_content_change(Path("/nonexistent/page.md"))

        assert result is None

    def test_find_page_matches_by_resolved_path(self, mock_site: MagicMock, tmp_path: Path) -> None:
        """Test that _find_page matches pages by resolved source path."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        md_file = content_dir / "about.md"
        md_file.write_text("---\ntitle: About\n---\nAbout content.")

        page = MagicMock()
        page.source_path = md_file
        mock_site.pages = [page]

        handler = ReactiveContentHandler(mock_site, mock_site.output_dir)
        found = handler._find_page(md_file)

        assert found is page

    def test_find_page_returns_none_for_unknown_path(
        self, mock_site: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _find_page returns None for path not in site.pages."""
        page = MagicMock()
        page.source_path = tmp_path / "content" / "other.md"
        mock_site.pages = [page]

        handler = ReactiveContentHandler(mock_site, mock_site.output_dir)
        found = handler._find_page(tmp_path / "content" / "unknown.md")

        assert found is None

    def test_handle_content_change_passes_output_collector_to_pipeline(
        self, mock_site: MagicMock, tmp_path: Path
    ) -> None:
        """Test that handle_content_change passes BuildOutputCollector to pipeline."""
        content_dir = tmp_path / "content"
        content_dir.mkdir(parents=True)
        md_file = content_dir / "page.md"
        md_file.write_text("---\ntitle: Test\n---\nBody")

        output_dir = tmp_path / "public"
        output_dir.mkdir()
        output_path = output_dir / "page" / "index.html"
        output_path.parent.mkdir(parents=True)
        output_path.write_text("<html></html>")

        page = MagicMock()
        page.source_path = md_file
        page._raw_content = "---\ntitle: Test\n---\nBody"
        page.html_content = "<p>Body</p>"
        page.output_path = output_path
        page._section = None
        mock_site.pages = [page]
        mock_site.output_dir = output_dir

        with patch("bengal.server.reactive.handler.RenderingPipeline") as mock_pipeline_cls:
            mock_pipeline = MagicMock()
            mock_pipeline_cls.return_value = mock_pipeline

            handler = ReactiveContentHandler(mock_site, output_dir)
            handler.handle_content_change(md_file)

            mock_pipeline_cls.assert_called_once()
            call_kwargs = mock_pipeline_cls.call_args[1]
            assert call_kwargs["output_collector"] is not None
