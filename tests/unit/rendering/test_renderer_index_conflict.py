from __future__ import annotations


import unittest
from pathlib import Path
from unittest.mock import MagicMock

from bengal.core.page import Page
from bengal.core.site import Site
from bengal.rendering.renderer import Renderer


class TestRendererIndexConflict(unittest.TestCase):
    def setUp(self):
        self.site = Site(Path("."))
        self.site.config = {"pagination": {"per_page": 10}}

        # Populate site.pages (regular_pages is a computed property derived from pages)
        self.site.pages = [Page(Path("content/home.md"), "", metadata={"title": "Home Page"})]

        self.mock_env = MagicMock()
        self.mock_template_engine = MagicMock()
        self.mock_template_engine.env = self.mock_env
        self.mock_template_engine.site = self.site

        # Capture context passed to render
        self.captured_context = None

        def capture_context(name, ctx):
            self.captured_context = ctx
            return "<html>rendered</html>"

        self.mock_template_engine.render.side_effect = capture_context

        self.renderer = Renderer(self.mock_template_engine)

    def test_tag_page_does_not_trigger_root_index_logic(self):
        """
        Regression test: Ensure generated tag pages (which look like index pages)
        don't accidentally trigger the "root home page" logic which overwrites 'posts'.
        """
        # Create a tag page
        # It has no section (page._section is None by default)
        # It ends in index.md (so is_index_page = True)
        # It IS generated
        tag_page = Page(
            Path("tags/mytag/index.md"),
            "",
            metadata={
                "type": "tag",
                "_tag": "mytag",
                "_tag_slug": "mytag",
                "_generated": True,
                "_posts": [Page(Path("content/p1.md"), "", metadata={"title": "Correct Post"})],
            },
        )

        # Verify setup matches the danger condition
        self.assertTrue(tag_page.source_path.stem in ("index", "_index"))
        self.assertIsNone(tag_page._section)
        self.assertTrue(tag_page.metadata.get("_generated"))

        # Render
        self.renderer.render_page(tag_page)

        # Get the context that was passed to template_engine.render
        context = self.captured_context
        self.assertIsNotNone(context, "Context was not captured from render call")

        # VERIFY: The posts should be the tagged post, NOT the home page
        posts = context.get("posts", [])
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].title, "Correct Post")

        # If the bug were present, it would have overwritten posts with site.regular_pages (Home Page)
        self.assertNotEqual(posts[0].title, "Home Page")


if __name__ == "__main__":
    unittest.main()
