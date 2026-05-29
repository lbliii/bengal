"""
Tests for renderer tag context handling.

Verifies proper resolution of tag pages, fallback behavior, and pagination context.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.core.site import Site
from bengal.rendering.renderer import Renderer
from bengal.utils.pagination import Paginator
from tests._testing.page_records import make_test_page


def _page(path: str, metadata: dict[str, object]):
    return make_test_page(source_path=Path(path), raw_content="", metadata=metadata)


@pytest.fixture
def site():
    """Create a basic site."""
    s = Site(Path("."))
    s.config = {"pagination": {"per_page": 10}}
    return s


@pytest.fixture
def renderer(site):
    """Create a renderer with mocked template engine."""
    mock_env = MagicMock()
    mock_template_engine = MagicMock()
    mock_template_engine.env = mock_env
    mock_template_engine.site = site

    return Renderer(mock_template_engine)


class TestTagContextRobustness:
    """Tests for tag page context robustness and fallback behavior."""

    def test_tag_context_with_empty_taxonomies(self, renderer, site):
        """When taxonomies are empty, should fallback to _posts metadata."""
        page1 = _page("content/p1.md", {"title": "P1", "tags": ["t1"]})
        page2 = _page("content/p2.md", {"title": "P2", "tags": ["t1"]})
        site.pages = [page1, page2]

        tag_page = _page(
            "tags/t1/index.html",
            {
                "type": "tag",
                "_tag": "t1",
                "_tag_slug": "t1",
                "_generated": True,
                "_posts": [page1, page2],
            },
        )

        # Empty taxonomies - should fallback to _posts
        site.taxonomies = {}
        context = {}
        renderer._add_generated_page_context(tag_page, context)

        assert "posts" in context
        assert len(context["posts"]) == 2
        assert context["posts"][0].title == "P1"

    def test_tag_context_with_stale_taxonomy_pages(self, renderer, site):
        """When resolution fails, should fallback to original taxonomy items."""
        page1 = _page("content/p1.md", {"title": "P1", "tags": ["t1"]})
        page2 = _page("content/p2.md", {"title": "P2", "tags": ["t1"]})

        tag_page = _page(
            "tags/t1/index.html",
            {
                "type": "tag",
                "_tag": "t1",
                "_tag_slug": "t1",
                "_generated": True,
                "_posts": [page1, page2],
            },
        )

        # Stale page object in taxonomy
        stale_page1 = _page("content/p1.md", {"title": "P1 Stale"})
        site.taxonomies = {"tags": {"t1": {"name": "t1", "pages": [stale_page1]}}}

        # Empty site.pages means resolution fails
        site.pages = []

        context = {}
        renderer._add_generated_page_context(tag_page, context)

        assert "posts" in context
        assert len(context["posts"]) == 1
        # Should have fallen back to the taxonomy page object
        assert context["posts"][0].title == "P1 Stale"


class TestTagContextResolution:
    """Tests for successful tag page resolution."""

    def test_resolution_returns_fresh_pages(self, renderer, site):
        """When resolution succeeds, should return fresh page objects."""
        fresh_page = _page("content/p1.md", {"title": "P1 Fresh", "tags": ["t1"]})
        site.pages = [fresh_page]

        # Stale page in taxonomy
        stale_page = _page("content/p1.md", {"title": "P1 Stale"})
        site.taxonomies = {"tags": {"t1": {"name": "t1", "pages": [stale_page]}}}

        tag_page = _page(
            "tags/t1/index.html",
            {"type": "tag", "_tag": "t1", "_tag_slug": "t1", "_generated": True},
        )

        context = {}
        renderer._add_generated_page_context(tag_page, context)

        assert "posts" in context
        assert len(context["posts"]) == 1
        # Should have resolved to FRESH page
        assert context["posts"][0].title == "P1 Fresh"


class TestTagContextPagination:
    """Tests for tag page pagination context."""

    def test_pagination_context_from_paginator(self, renderer, site):
        """Pagination context should come from the paginator."""
        page1 = _page("content/p1.md", {"title": "P1 Fresh", "tags": ["t1"]})
        page2 = _page("content/p2.md", {"title": "P2 Fresh", "tags": ["t1"]})
        site.pages = [page1, page2]

        site.taxonomies = {"tags": {"t1": {"name": "t1", "pages": [page1, page2]}}}

        tag_page = _page(
            "tags/t1/index.html",
            {
                "type": "tag",
                "_tag": "t1",
                "_tag_slug": "t1",
                "_generated": True,
                "_page_num": 2,
                "_paginator": Paginator([page1, page2], per_page=1),
            },
        )

        context = {}
        renderer._add_generated_page_context(tag_page, context)

        assert "posts" in context
        assert [p.title for p in context["posts"]] == ["P2 Fresh"]
        assert context["current_page"] == 2
        assert context["total_pages"] == 2
        assert context["has_prev"] is True
        assert context["has_next"] is False
        assert context["base_url"] == "/tags/t1/"
