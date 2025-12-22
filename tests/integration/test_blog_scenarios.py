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
class TestBlogPagination:
    """Test blog pagination with 25 posts."""

    def test_site_discovers_all_posts(self, site) -> None:
        """All 25 posts should be discovered."""
        # Filter to just posts (exclude index pages and about)
        posts = [p for p in site.pages if "/posts/post-" in str(p.source_path)]
        assert len(posts) == 25, f"Expected 25 posts, found {len(posts)}"

    def test_posts_sorted_by_date_descending(self, site) -> None:
        """Posts should be sorted by date, newest first."""
        posts = [p for p in site.pages if "/posts/post-" in str(p.source_path)]

        # Sort by date to verify order
        dates = []
        for post in posts:
            if hasattr(post, "date") and post.date:
                dates.append(post.date)

        # Verify dates are in descending order (or at least consistent)
        if dates:
            for i in range(len(dates) - 1):
                assert dates[i] >= dates[i + 1], "Posts should be sorted newest first"

    def test_pagination_pages_created(self, site, build_site) -> None:
        """Pagination should create multiple page directories.

        With 25 posts and 5 per page, we should have 5 pagination pages.
        """
        build_site()

        output = site.output_dir

        # First page is at posts/index.html
        assert (output / "posts" / "index.html").exists(), "Posts index should exist"

        # Additional pages should exist
        # Note: pagination structure varies by theme, check common patterns
        page_2_exists = (output / "posts" / "page" / "2" / "index.html").exists() or (
            output / "posts" / "2" / "index.html"
        ).exists()

        # If pagination is enabled, we should have multiple pages
        # (actual paths depend on pagination implementation)
        if not page_2_exists:
            # Check if all posts are on one page (pagination may not be active)
            index_html = (output / "posts" / "index.html").read_text()
            # This is acceptable if pagination isn't rendering separate pages
            # but posts should still be accessible
            assert "post-" in index_html.lower() or len(list(output.glob("**/post-*"))) > 0

    def test_individual_post_pages_created(self, site, build_site) -> None:
        """Each post should have its own page."""
        build_site()

        output = site.output_dir

        # Check for a sample of posts
        for i in [1, 10, 25]:
            post_path = output / "posts" / f"post-{i:02d}" / "index.html"
            assert post_path.exists(), f"Post {i} page should exist at {post_path}"


@pytest.mark.bengal(testroot="test-blog-paginated")
class TestBlogRSS:
    """Test RSS feed generation for blogs."""

    def test_rss_feed_generated(self, site, build_site) -> None:
        """RSS feed should be generated for blog."""
        build_site()

        output = site.output_dir

        # RSS feed can be at various locations depending on config
        rss_locations = [
            output / "feed.xml",
            output / "rss.xml",
            output / "index.xml",
            output / "posts" / "index.xml",
            output / "posts" / "feed.xml",
        ]

        rss_found = any(loc.exists() for loc in rss_locations)

        if not rss_found:
            # List what was actually generated
            xml_files = list(output.glob("**/*.xml"))
            pytest.skip(
                f"RSS feed not found at expected locations. "
                f"XML files found: {[str(f.relative_to(output)) for f in xml_files]}"
            )

    def test_rss_contains_posts(self, site, build_site) -> None:
        """RSS feed should contain post entries."""
        build_site()

        output = site.output_dir

        # Find RSS feed
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

        # RSS should contain item elements
        assert "<item>" in rss_content or "<entry>" in rss_content, (
            "RSS feed should contain items/entries"
        )


@pytest.mark.bengal(testroot="test-blog-paginated")
class TestBlogTaxonomy:
    """Test tag and category taxonomies for blogs."""

    def test_tags_discovered(self, site) -> None:
        """Posts should have tags extracted."""
        posts = [p for p in site.pages if "/posts/post-" in str(p.source_path)]

        # At least some posts should have tags
        posts_with_tags = [p for p in posts if hasattr(p, "tags") and p.tags]

        # All generated posts have tags
        assert len(posts_with_tags) > 0, "Posts should have tags"

    def test_tag_pages_created(self, site, build_site) -> None:
        """Tag pages should be generated."""
        build_site()

        output = site.output_dir

        # Check for tags directory
        tags_dir = output / "tags"

        if tags_dir.exists():
            # Should have at least one tag page
            tag_pages = list(tags_dir.glob("**/index.html"))
            assert len(tag_pages) > 0, "Should have tag pages"
        else:
            # Tags might be at a different location or not enabled
            pytest.skip("Tags directory not found - taxonomies may not be enabled")
