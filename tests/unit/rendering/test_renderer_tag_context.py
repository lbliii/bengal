import unittest
from pathlib import Path
from unittest.mock import MagicMock

from bengal.core.page import Page
from bengal.core.site import Site
from bengal.rendering.renderer import Renderer


class TestRendererTagContext(unittest.TestCase):
    def setUp(self):
        self.site = Site(Path("."))
        self.site.config = {"pagination": {"per_page": 10}}

        self.mock_env = MagicMock()
        self.mock_template_engine = MagicMock()
        self.mock_template_engine.env = self.mock_env
        self.mock_template_engine.site = self.site

        self.renderer = Renderer(self.mock_template_engine)

    def test_add_generated_page_context_tag_robustness(self):
        # Setup pages
        page1 = Page(Path("content/p1.md"), "", metadata={"title": "P1", "tags": ["t1"]})
        page2 = Page(Path("content/p2.md"), "", metadata={"title": "P2", "tags": ["t1"]})
        self.site.pages = [page1, page2]

        # Setup tag page with _posts
        tag_page = Page(
            Path("tags/t1/index.html"),
            "",
            metadata={
                "type": "tag",
                "_tag": "t1",
                "_tag_slug": "t1",
                "_generated": True,
                "_posts": [page1, page2],
            },
        )

        # SCENARIO 1: Taxonomies empty (should fallback to _posts)
        self.site.taxonomies = {}
        context = {}
        self.renderer._add_generated_page_context(tag_page, context)

        self.assertIn("posts", context)
        self.assertEqual(len(context["posts"]), 2)
        self.assertEqual(context["posts"][0].title, "P1")

        # SCENARIO 2: Taxonomies present but resolution fails (should fallback to original items)
        # We simulate this by having tax objects that are NOT in site.pages
        # But since we are testing resolution failure, we need site.pages to NOT contain them

        # Create "stale" page objects for taxonomy
        stale_page1 = Page(Path("content/p1.md"), "", metadata={"title": "P1 Stale"})

        self.site.taxonomies = {"tags": {"t1": {"name": "t1", "pages": [stale_page1]}}}
        # site.pages is empty (so resolution fails)
        self.site.pages = []

        context = {}
        self.renderer._add_generated_page_context(tag_page, context)

        self.assertIn("posts", context)
        self.assertEqual(len(context["posts"]), 1)
        # Should have fallen back to the taxonomy page object
        self.assertEqual(context["posts"][0].title, "P1 Stale")

    def test_add_generated_page_context_resolution_success(self):
        # Setup pages
        page1 = Page(Path("content/p1.md"), "", metadata={"title": "P1 Fresh", "tags": ["t1"]})
        self.site.pages = [page1]

        # Stale page in taxonomy
        stale_page1 = Page(Path("content/p1.md"), "", metadata={"title": "P1 Stale"})

        self.site.taxonomies = {"tags": {"t1": {"name": "t1", "pages": [stale_page1]}}}

        tag_page = Page(
            Path("tags/t1/index.html"),
            "",
            metadata={"type": "tag", "_tag": "t1", "_tag_slug": "t1", "_generated": True},
        )

        context = {}
        self.renderer._add_generated_page_context(tag_page, context)

        self.assertIn("posts", context)
        self.assertEqual(len(context["posts"]), 1)
        # Should have resolved to FRESH page
        self.assertEqual(context["posts"][0].title, "P1 Fresh")


if __name__ == "__main__":
    unittest.main()
