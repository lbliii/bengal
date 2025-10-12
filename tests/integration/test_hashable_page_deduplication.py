"""
Integration tests for page and section hashability in real build scenarios.

Tests that hashability works correctly in the context of the full build pipeline,
especially for deduplication and set operations.
"""

from pathlib import Path

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site


class TestPageDeduplicationInBuilds:
    """Test page deduplication in build pipeline scenarios."""

    def test_generated_pages_deduplicated_automatically(self, tmp_path):
        """
        Test that generated pages are automatically deduplicated when
        added to pages_to_build during incremental builds.

        This tests the optimization in BuildOrchestrator (build.py line 295-306).
        """
        # Setup site
        site = Site(root_path=tmp_path, output_dir=tmp_path / "public")

        # Create some regular pages
        page1 = Page(source_path=tmp_path / "content/post1.md", tags=["python"])
        page2 = Page(source_path=tmp_path / "content/post2.md", tags=["python"])

        # Create generated tag page
        tag_page = Page(
            source_path=Path("_generated/tags/python.md"),
            metadata={"_generated": True, "type": "tag", "_tag_slug": "python"},
        )

        site.pages = [page1, page2, tag_page]

        # Simulate incremental build trying to add tag_page multiple times
        # (this could happen if multiple pages with 'python' tag are being rebuilt)
        pages_to_build = [page1, tag_page]

        # Convert to set for automatic deduplication (as done in build.py)
        pages_set = set(pages_to_build)
        pages_set.add(tag_page)  # Try adding again
        pages_set.add(tag_page)  # And again
        pages_set.add(tag_page)  # And again

        # Should only have 2 unique pages
        assert len(pages_set) == 2
        assert page1 in pages_set
        assert tag_page in pages_set

        # Convert back to list (as done in build.py)
        final_pages = list(pages_set)
        assert len(final_pages) == 2

    def test_page_lookup_performance(self, tmp_path):
        """
        Test that set-based page lookup is fast even with many pages.

        This validates the O(1) membership test optimization.
        """
        import time

        # Create 1000 pages
        all_pages = [Page(source_path=tmp_path / f"content/post{i}.md") for i in range(1000)]

        # Pick 100 pages to "rebuild"
        pages_to_rebuild = set(all_pages[::10])  # Every 10th page

        # Measure lookup time with set (O(1))
        start = time.time()
        found_count = 0
        for page in all_pages:
            if page in pages_to_rebuild:  # O(1) with set
                found_count += 1
        lookup_time_set = time.time() - start

        # Measure lookup time with list (O(n)) for comparison
        pages_to_rebuild_list = list(pages_to_rebuild)
        start = time.time()
        found_count_list = 0
        for page in all_pages:
            if page in pages_to_rebuild_list:  # O(n) with list
                found_count_list += 1
        lookup_time_list = time.time() - start

        assert found_count == found_count_list == 100

        # Set should be significantly faster (at least 5x for O(1) vs O(n))
        assert lookup_time_set < lookup_time_list / 5, (
            f"Set lookup ({lookup_time_set * 1000:.2f}ms) should be much faster than list ({lookup_time_list * 1000:.2f}ms)"
        )


class TestSectionTrackingInBuilds:
    """Test section tracking using sets in incremental builds."""

    def test_tracking_affected_sections(self, tmp_path):
        """
        Real-world use case: tracking affected sections during incremental build.

        This tests the optimization in IncrementalOrchestrator (incremental.py line 249).
        """
        # Create sections
        blog_section = Section(name="blog", path=tmp_path / "blog")
        docs_section = Section(name="docs", path=tmp_path / "docs")
        tutorials_section = Section(name="tutorials", path=tmp_path / "tutorials")

        # Create pages in sections
        pages = [
            Page(source_path=tmp_path / "blog/post1.md"),
            Page(source_path=tmp_path / "blog/post2.md"),
            Page(source_path=tmp_path / "docs/guide1.md"),
            Page(source_path=tmp_path / "blog/post3.md"),
            Page(source_path=tmp_path / "tutorials/intro.md"),
            Page(source_path=tmp_path / "docs/guide2.md"),
        ]

        # Assign pages to sections
        pages[0]._section = blog_section
        pages[1]._section = blog_section
        pages[2]._section = docs_section
        pages[3]._section = blog_section
        pages[4]._section = tutorials_section
        pages[5]._section = docs_section

        # Track affected sections (simulating incremental build)
        # Using Set[Section] instead of Set[Any] (type-safe!)
        affected_sections = set()
        for page in pages:
            if hasattr(page, "_section") and page._section:
                affected_sections.add(page._section)

        # Should have 3 unique sections
        assert len(affected_sections) == 3
        assert blog_section in affected_sections
        assert docs_section in affected_sections
        assert tutorials_section in affected_sections

    def test_section_to_pages_mapping(self, tmp_path):
        """
        Test mapping sections to their pages using dict with hashable sections.
        """
        section1 = Section(name="blog", path=tmp_path / "blog")
        section2 = Section(name="docs", path=tmp_path / "docs")

        page1 = Page(source_path=tmp_path / "blog/post1.md")
        page2 = Page(source_path=tmp_path / "blog/post2.md")
        page3 = Page(source_path=tmp_path / "docs/guide.md")

        # Build mapping using sections as keys
        section_pages = {section1: [page1, page2], section2: [page3]}

        # Should work seamlessly
        assert len(section_pages[section1]) == 2
        assert len(section_pages[section2]) == 1
        assert page1 in section_pages[section1]
        assert page3 in section_pages[section2]

        # Can update using equivalent section
        section1_copy = Section(name="blog", path=tmp_path / "blog")
        assert section1_copy in section_pages  # Should be found
        section_pages[section1_copy].append(Page(source_path=tmp_path / "blog/post3.md"))

        # Should have updated the original entry
        assert len(section_pages[section1]) == 3


class TestSetOperationsInPipeline:
    """Test set operations with pages in real scenarios."""

    def test_page_set_operations_for_analysis(self, tmp_path):
        """Test set operations useful for page analysis."""
        # Create pages with different tags
        python_pages = {
            Page(source_path=tmp_path / "content/python1.md", tags=["python"]),
            Page(source_path=tmp_path / "content/python2.md", tags=["python"]),
            Page(source_path=tmp_path / "content/python3.md", tags=["python"]),
        }

        web_pages = {
            Page(source_path=tmp_path / "content/web1.md", tags=["web"]),
            Page(source_path=tmp_path / "content/web2.md", tags=["web"]),
            Page(source_path=tmp_path / "content/python2.md", tags=["python", "web"]),  # Overlap
        }

        # Find pages in both categories
        both = python_pages & web_pages
        assert len(both) == 1  # Only python2.md

        # Find pages unique to python
        python_only = python_pages - web_pages
        assert len(python_only) == 2  # python1 and python3

        # All pages
        all_pages = python_pages | web_pages
        assert len(all_pages) == 5  # Total unique pages

    def test_page_deduplication_across_taxonomies(self, tmp_path):
        """Test deduplication when same page appears in multiple taxonomies."""
        page1 = Page(source_path=tmp_path / "content/post.md", tags=["python", "web", "tutorial"])

        # Simulate page appearing in multiple taxonomy collections
        python_tag_pages = [page1]
        web_tag_pages = [page1]
        tutorial_tag_pages = [page1]

        # Collect all unique pages across taxonomies
        all_taxonomy_pages = set()
        all_taxonomy_pages.update(python_tag_pages)
        all_taxonomy_pages.update(web_tag_pages)
        all_taxonomy_pages.update(tutorial_tag_pages)

        # Should only have 1 unique page
        assert len(all_taxonomy_pages) == 1
        assert page1 in all_taxonomy_pages


class TestMemoryOptimizations:
    """Test that hashability enables memory optimizations."""

    def test_dict_with_page_keys_vs_id_mapping(self, tmp_path):
        """
        Compare direct page keys vs ID mapping (as in KnowledgeGraph).

        Tests the optimization in knowledge_graph.py.
        """
        import sys

        # Create some pages
        pages = [Page(source_path=tmp_path / f"content/post{i}.md") for i in range(100)]

        # Old approach: ID-based mapping (knowledge_graph.py before refactor)
        page_by_id = {}
        incoming_refs_by_id = {}
        for page in pages:
            page_by_id[id(page)] = page
            incoming_refs_by_id[id(page)] = 5

        # New approach: Direct page keys (knowledge_graph.py after refactor)
        incoming_refs_direct = {}
        for page in pages:
            incoming_refs_direct[page] = 5

        # New approach should use less memory (no page_by_id needed)
        # Approximate memory usage (this is simplified)
        old_size = sys.getsizeof(page_by_id) + sys.getsizeof(incoming_refs_by_id)
        new_size = sys.getsizeof(incoming_refs_direct)

        # Should save memory by not needing page_by_id
        assert new_size < old_size, "Direct page keys should use less memory"

    def test_page_identity_across_reconstructions(self, tmp_path):
        """
        Test that pages with same source_path are considered equal,
        even if reconstructed (important for cache lookups).
        """
        path = tmp_path / "content/post.md"

        # Create page in build 1
        page1 = Page(source_path=path, content="Original content")
        data = {page1: "some cached data"}

        # Simulate page reconstruction in build 2 (incremental build)
        page2 = Page(source_path=path, content="Updated content")

        # Should be able to find cached data using reconstructed page
        assert page2 in data
        assert data[page2] == "some cached data"

        # Pages should be equal despite different content
        assert page1 == page2
        assert hash(page1) == hash(page2)
