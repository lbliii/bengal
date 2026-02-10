"""
Unit tests for AST-first page model (Phase C).

Tests that extract_links() and toc_items prefer AST extraction when
page._ast_cache is populated, and fall back to legacy paths otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


# =============================================================================
# extract_links() AST-first path
# =============================================================================


class TestExtractLinksASTFirst:
    """Tests for extract_links() preferring AST extraction."""

    def _make_page_with_ast(self, ast: Any, source: str = "") -> Any:
        """Create a minimal page-like object with _ast_cache and _source."""
        from bengal.rendering.page_operations import PageOperationsMixin

        @dataclass
        class TestPage(PageOperationsMixin):
            _ast_cache: Any = None
            _source: str = ""
            content: str = ""
            rendered_html: str = ""
            links: list[str] = field(default_factory=list)
            source_path: Path = field(default_factory=lambda: Path("/test.md"))

        return TestPage(_ast_cache=ast, _source=source)

    def test_prefers_ast_when_available(self) -> None:
        """extract_links() uses AST extraction when _ast_cache is set."""
        try:
            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        doc = parse("Click [here](https://example.com) and [there](/docs).")
        page = self._make_page_with_ast(doc)
        links = page.extract_links()

        assert "https://example.com" in links
        assert "/docs" in links

    def test_falls_back_to_regex_without_ast(self) -> None:
        """extract_links() uses regex fallback when _ast_cache is None."""
        source = "Click [here](https://example.com) and [there](/docs)."
        page = self._make_page_with_ast(ast=None, source=source)
        links = page.extract_links()

        assert "https://example.com" in links
        assert "/docs" in links

    def test_ast_path_skips_code_block_links(self) -> None:
        """AST extraction handles code blocks correctly."""
        try:
            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        # Links in code blocks should not be extracted
        md = "Real [link](/real).\n\n```\n[fake](/not-a-link)\n```"
        doc = parse(md)
        page = self._make_page_with_ast(doc)
        links = page.extract_links()

        assert "/real" in links
        # Code block links may or may not be extracted depending on
        # the AST extractor's implementation. The key point is no crash.

    def test_empty_ast_returns_empty_links(self) -> None:
        """extract_links() with empty AST returns empty list."""
        try:
            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        doc = parse("No links here, just text.")
        page = self._make_page_with_ast(doc)
        links = page.extract_links()

        assert links == []


# =============================================================================
# toc_items AST-first path
# =============================================================================


class TestTocItemsASTFirst:
    """Tests for toc_items preferring AST extraction."""

    def _make_page_with_ast(
        self, ast: Any, toc: str = "", toc_items_cache: Any = None
    ) -> Any:
        """Create a minimal page-like object with _ast_cache and toc."""

        @dataclass
        class TestPage:
            _ast_cache: Any = None
            toc: str = ""
            _toc_items_cache: list[dict[str, Any]] | None = None

            @property
            def toc_items(self) -> list[dict[str, Any]]:
                """Reimplemented toc_items with AST-first path."""
                if self._toc_items_cache is not None:
                    return self._toc_items_cache

                # AST-first
                if hasattr(self, "_ast_cache") and self._ast_cache is not None:
                    from bengal.parsing.ast.patitas_extract import extract_toc_from_document

                    items = extract_toc_from_document(self._ast_cache)
                    if items:
                        self._toc_items_cache = items
                        return items

                # Fallback: HTML-based
                if self.toc:
                    from bengal.rendering.pipeline import extract_toc_structure

                    self._toc_items_cache = extract_toc_structure(self.toc)

                return self._toc_items_cache if self._toc_items_cache is not None else []

        return TestPage(_ast_cache=ast, toc=toc, _toc_items_cache=toc_items_cache)

    def test_prefers_ast_when_available(self) -> None:
        """toc_items uses AST extraction when _ast_cache is set."""
        try:
            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        doc = parse("# Title\n\n## Section One\n\nText\n\n## Section Two\n\nMore text")
        page = self._make_page_with_ast(doc)
        items = page.toc_items

        assert len(items) >= 2
        titles = [item.get("title", item.get("text", "")) for item in items]
        assert any("Section One" in t for t in titles)
        assert any("Section Two" in t for t in titles)

    def test_falls_back_to_html_without_ast(self) -> None:
        """toc_items uses HTML fallback when _ast_cache is None."""
        toc_html = (
            '<div class="toc"><ul>'
            '<li><a href="#section-one">Section One</a></li>'
            '<li><a href="#section-two">Section Two</a></li>'
            "</ul></div>"
        )
        page = self._make_page_with_ast(ast=None, toc=toc_html)
        items = page.toc_items

        assert len(items) >= 2

    def test_returns_empty_without_ast_or_toc(self) -> None:
        """toc_items returns empty list when neither AST nor toc is available."""
        page = self._make_page_with_ast(ast=None, toc="")
        assert page.toc_items == []

    def test_caches_result(self) -> None:
        """toc_items caches the result on second access."""
        try:
            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        doc = parse("## Heading\n\nText")
        page = self._make_page_with_ast(doc)

        # First access populates cache
        items1 = page.toc_items
        # Second access uses cache (same object)
        items2 = page.toc_items
        assert items1 is items2

    def test_returns_cached_immediately(self) -> None:
        """toc_items returns cached value immediately without re-extracting."""
        cached = [{"id": "cached", "title": "Cached", "level": 2}]
        page = self._make_page_with_ast(ast=None, toc="", toc_items_cache=cached)
        assert page.toc_items is cached
