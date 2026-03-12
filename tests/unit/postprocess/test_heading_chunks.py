"""Unit tests for extract_heading_chunks in output_formats.utils."""

from __future__ import annotations

from bengal.postprocess.output_formats.utils import extract_heading_chunks


class TestExtractHeadingChunks:
    def test_splits_by_heading_boundaries(self) -> None:
        html = (
            '<h2 id="install">Installation</h2><p>Use pip install.</p>'
            '<h3 id="config">Config</h3><p>Edit bengal.toml.</p>'
        )
        toc = [
            {"id": "install", "title": "Installation", "level": 1},
            {"id": "config", "title": "Config", "level": 2},
        ]
        chunks = extract_heading_chunks(html, toc, "/docs/install/")
        assert len(chunks) == 2
        assert chunks[0]["anchor"] == "install"
        assert chunks[0]["anchor_url"] == "/docs/install#install"
        assert chunks[0]["title"] == "Installation"
        assert chunks[0]["level"] == 1
        assert "pip install" in chunks[0]["content"]
        assert chunks[1]["anchor"] == "config"
        assert chunks[1]["anchor_url"] == "/docs/install#config"
        assert "bengal.toml" in chunks[1]["content"]
        assert "content_hash" in chunks[0]

    def test_empty_html_returns_empty(self) -> None:
        assert extract_heading_chunks("", [], "/") == []

    def test_empty_toc_still_chunks_by_headings(self) -> None:
        html = '<h2 id="x">X</h2><p>Content</p>'
        chunks = extract_heading_chunks(html, [], "/")
        assert len(chunks) == 1
        assert chunks[0]["anchor"] == "x"
        assert chunks[0]["title"] == ""

    def test_no_headings_with_id_returns_single_chunk(self) -> None:
        html = "<p>No headings with id.</p>"
        toc = []
        chunks = extract_heading_chunks(html, toc, "/page/")
        assert len(chunks) == 1
        assert chunks[0]["anchor"] == ""
        assert chunks[0]["anchor_url"] == "/page"
        assert "No headings" in chunks[0]["content"]

    def test_strips_html_from_content(self) -> None:
        html = '<h2 id="x">X</h2><p>Plain <strong>text</strong> here.</p>'
        toc = [{"id": "x", "title": "X", "level": 1}]
        chunks = extract_heading_chunks(html, toc, "/")
        assert "<strong>" not in chunks[0]["content"]
        assert "Plain text here" in chunks[0]["content"]

    def test_captures_content_before_first_heading(self) -> None:
        html = '<p>Introduction paragraph.</p><h2 id="details">Details</h2><p>Detail content.</p>'
        toc = [{"id": "details", "title": "Details", "level": 2}]
        chunks = extract_heading_chunks(html, toc, "/docs/page/")
        assert len(chunks) == 2
        assert chunks[0]["anchor"] == ""
        assert "Introduction paragraph" in chunks[0]["content"]
        assert chunks[1]["anchor"] == "details"
        assert "Detail content" in chunks[1]["content"]
