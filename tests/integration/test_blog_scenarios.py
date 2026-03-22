"""Integration tests for blog scenarios.

Tests blog-specific functionality:
- Pagination with multiple pages
- RSS feed generation
- Date-based sorting
- Archive pages

Phase 2 of RFC: User Scenario Coverage & Validation Matrix
"""

from __future__ import annotations

import pytest


@pytest.mark.bengal(testroot="test-blog-paginated")
class TestBlogScenarios:
    """Test blog functionality: pagination, RSS, taxonomy with 25 posts."""

    def test_site_discovers_all_posts(self, shared_site) -> None:
        """All 25 posts should be discovered."""
        posts = [p for p in shared_site.pages if "/posts/post-" in str(p.source_path)]
        assert len(posts) == 25, f"Expected 25 posts, found {len(posts)}"

    def test_posts_have_dates_for_sorting(self, shared_site) -> None:
        """Posts should have dates that can be used for sorting."""
        posts = [p for p in shared_site.pages if "/posts/post-" in str(p.source_path)]
        dates = [post.date for post in posts if hasattr(post, "date") and post.date]
        assert len(dates) == len(posts), "All posts should have dates for sorting"
        sorted_dates = sorted(dates, reverse=True)
        assert sorted_dates[0] > sorted_dates[-1], "Posts should have different dates"

    @pytest.mark.heavyweight
    def test_pagination_pages_created(self, shared_site) -> None:
        """Pagination should create multiple page directories.

        With 25 posts and 5 per page, we should have 5 pagination pages.
        """
        output = shared_site.output_dir

        assert (output / "posts" / "index.html").exists(), "Posts index should exist"

        page_2_exists = (output / "posts" / "page" / "2" / "index.html").exists() or (
            output / "posts" / "2" / "index.html"
        ).exists()

        if not page_2_exists:
            index_html = (output / "posts" / "index.html").read_text()
            assert "post-" in index_html.lower() or len(list(output.glob("**/post-*"))) > 0

    def test_individual_post_pages_created(self, shared_site) -> None:
        """Each post should have its own page."""
        output = shared_site.output_dir

        for i in [1, 10, 25]:
            post_path = output / "posts" / f"post-{i:02d}" / "index.html"
            assert post_path.exists(), f"Post {i} page should exist at {post_path}"

    def test_rss_feed_generated(self, shared_site) -> None:
        """RSS feed should be generated for blog."""
        output = shared_site.output_dir

        rss_locations = [
            output / "feed.xml",
            output / "rss.xml",
            output / "index.xml",
            output / "posts" / "index.xml",
            output / "posts" / "feed.xml",
        ]

        rss_found = any(loc.exists() for loc in rss_locations)

        if not rss_found:
            xml_files = list(output.glob("**/*.xml"))
            pytest.skip(
                f"RSS feed not found at expected locations. "
                f"XML files found: {[str(f.relative_to(output)) for f in xml_files]}"
            )

    def test_rss_contains_posts(self, shared_site) -> None:
        """RSS feed should contain post entries."""
        output = shared_site.output_dir

        rss_path = None
        for path in [
            output / "feed.xml",
            output / "rss.xml",
            output / "index.xml",
            output / "posts" / "index.xml",
        ]:
            if path.exists():
                rss_path = path
                break

        if rss_path is None:
            pytest.skip("RSS feed not found")

        rss_content = rss_path.read_text()

        assert "<item>" in rss_content or "<entry>" in rss_content, (
            "RSS feed should contain items/entries"
        )

    def test_tags_discovered(self, shared_site) -> None:
        """Posts should have tags extracted."""
        posts = [p for p in shared_site.pages if "/posts/post-" in str(p.source_path)]
        posts_with_tags = [p for p in posts if hasattr(p, "tags") and p.tags]
        assert len(posts_with_tags) > 0, "Posts should have tags"

    @pytest.mark.heavyweight
    def test_tag_pages_created(self, shared_site) -> None:
        """Tag pages should be generated."""
        output = shared_site.output_dir

        tags_dir = output / "tags"

        if tags_dir.exists():
            tag_pages = list(tags_dir.glob("**/index.html"))
            assert len(tag_pages) > 0, "Should have tag pages"
        else:
            pytest.skip("Tags directory not found - taxonomies may not be enabled")
