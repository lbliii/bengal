"""
Tests for renderer index page conflict handling.

Verifies that generated tag pages (which look like index pages) don't
accidentally trigger the "root home page" logic.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.core.page import Page
from bengal.core.site import Site
from bengal.rendering.renderer import Renderer


@pytest.fixture
def site():
    """Create a site with a home page."""
    s = Site(Path("."))
    s.config = {"pagination": {"per_page": 10}}
    s.pages = [Page(Path("content/home.md"), "", _raw_metadata={"title": "Home Page"})]
    return s


@pytest.fixture
def renderer(site):
    """Create a renderer with mocked template engine."""
    mock_env = MagicMock()
    mock_template_engine = MagicMock()
    mock_template_engine.env = mock_env
    mock_template_engine.site = site

    # Context capture for assertions
    captured = {"context": None}

    def capture_context(name, ctx):
        captured["context"] = ctx
        return "<html>rendered</html>"

    mock_template_engine.render.side_effect = capture_context

    r = Renderer(mock_template_engine)
    r._captured = captured
    return r


def test_tag_page_does_not_trigger_root_index_logic(renderer):
    """
    Regression test: Generated tag pages (which look like index pages)
    don't accidentally trigger the "root home page" logic which overwrites 'posts'.

    """
    # Create a tag page - it has no section, ends in index.md, and is generated
    tag_page = Page(
        Path("tags/mytag/index.md"),
        "",
        metadata={
            "type": "tag",
            "_tag": "mytag",
            "_tag_slug": "mytag",
            "_generated": True,
            "_posts": [Page(Path("content/p1.md"), "", _raw_metadata={"title": "Correct Post"})],
        },
    )

    # Verify setup matches the danger condition
    assert tag_page.source_path.stem in ("index", "_index")
    assert tag_page._section is None
    assert tag_page.metadata.get("_generated") is True

    # Render
    renderer.render_page(tag_page)

    # Get captured context
    context = renderer._captured["context"]
    assert context is not None, "Context was not captured from render call"

    # VERIFY: The posts should be the tagged post, NOT the home page
    posts = context.get("posts", [])
    assert len(posts) == 1
    assert posts[0].title == "Correct Post"

    # If the bug were present, it would have overwritten posts with site.regular_pages
    assert posts[0].title != "Home Page"
