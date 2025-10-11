"""
Tests for weight-based sorting in ContentDiscovery.

Tests that content discovery automatically sorts pages and sections
by weight after discovering content.
"""

from bengal.discovery.content_discovery import ContentDiscovery


class TestContentDiscoverySorting:
    """Test that ContentDiscovery sorts content by weight."""

    def test_discover_sorts_pages_in_section(self, tmp_path):
        """Pages within a section are sorted by weight after discovery."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create section directory
        section_dir = content_dir / "docs"
        section_dir.mkdir()

        # Create pages with different weights
        (section_dir / "page-z.md").write_text("""---
title: Z Page
weight: 10
---
Content""")

        (section_dir / "page-a.md").write_text("""---
title: A Page
weight: 1
---
Content""")

        (section_dir / "page-m.md").write_text("""---
title: M Page
weight: 5
---
Content""")

        # Discover content
        discovery = ContentDiscovery(content_dir)
        sections, pages = discovery.discover()

        # Find the docs section
        docs_section = sections[0]

        # Pages should be sorted by weight
        assert len(docs_section.pages) == 3
        assert docs_section.pages[0].metadata["weight"] == 1
        assert docs_section.pages[1].metadata["weight"] == 5
        assert docs_section.pages[2].metadata["weight"] == 10

    def test_discover_sorts_subsections(self, tmp_path):
        """Subsections within a section are sorted by weight after discovery."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create parent section
        section_dir = content_dir / "docs"
        section_dir.mkdir()

        # Create subsections with index pages that have weights
        sub1_dir = section_dir / "advanced"
        sub1_dir.mkdir()
        (sub1_dir / "_index.md").write_text("""---
title: Advanced
weight: 100
---
Content""")

        sub2_dir = section_dir / "beginner"
        sub2_dir.mkdir()
        (sub2_dir / "_index.md").write_text("""---
title: Beginner
weight: 1
---
Content""")

        sub3_dir = section_dir / "intermediate"
        sub3_dir.mkdir()
        (sub3_dir / "_index.md").write_text("""---
title: Intermediate
weight: 50
---
Content""")

        # Discover content
        discovery = ContentDiscovery(content_dir)
        sections, pages = discovery.discover()

        # Find the docs section
        docs_section = sections[0]

        # Subsections should be sorted by weight
        assert len(docs_section.subsections) == 3
        assert docs_section.subsections[0].metadata["weight"] == 1
        assert docs_section.subsections[1].metadata["weight"] == 50
        assert docs_section.subsections[2].metadata["weight"] == 100

    def test_discover_sorts_top_level_sections(self, tmp_path):
        """Top-level sections are sorted by weight after discovery."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create top-level sections with weights
        section1_dir = content_dir / "zebra"
        section1_dir.mkdir()
        (section1_dir / "_index.md").write_text("""---
title: Zebra
weight: 100
---
Content""")
        (section1_dir / "page.md").write_text("Content")  # Need content to be discovered

        section2_dir = content_dir / "alpha"
        section2_dir.mkdir()
        (section2_dir / "_index.md").write_text("""---
title: Alpha
weight: 1
---
Content""")
        (section2_dir / "page.md").write_text("Content")

        section3_dir = content_dir / "moose"
        section3_dir.mkdir()
        (section3_dir / "_index.md").write_text("""---
title: Moose
weight: 50
---
Content""")
        (section3_dir / "page.md").write_text("Content")

        # Discover content
        discovery = ContentDiscovery(content_dir)
        sections, pages = discovery.discover()

        # Top-level sections should be sorted by weight
        assert len(sections) == 3
        assert sections[0].metadata["weight"] == 1    # alpha
        assert sections[1].metadata["weight"] == 50   # moose
        assert sections[2].metadata["weight"] == 100  # zebra

    def test_discover_sorts_nested_sections_recursively(self, tmp_path):
        """Nested sections are sorted recursively at all levels."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create parent section
        parent_dir = content_dir / "docs"
        parent_dir.mkdir()
        (parent_dir / "_index.md").write_text("""---
title: Docs
weight: 1
---
Content""")

        # Create child sections
        child1_dir = parent_dir / "advanced"
        child1_dir.mkdir()
        (child1_dir / "_index.md").write_text("""---
title: Advanced
weight: 100
---
Content""")
        # Advanced needs a page to be discovered
        (child1_dir / "page.md").write_text("Content")

        child2_dir = parent_dir / "beginner"
        child2_dir.mkdir()
        (child2_dir / "_index.md").write_text("""---
title: Beginner
weight: 1
---
Content""")
        # Beginner needs at least one page to be discovered
        (child2_dir / "intro.md").write_text("Content")

        # Create grandchild sections under beginner
        grandchild1_dir = child2_dir / "tutorial-z"
        grandchild1_dir.mkdir()
        (grandchild1_dir / "_index.md").write_text("""---
title: Tutorial Z
weight: 50
---
Content""")
        (grandchild1_dir / "page.md").write_text("Content")

        grandchild2_dir = child2_dir / "tutorial-a"
        grandchild2_dir.mkdir()
        (grandchild2_dir / "_index.md").write_text("""---
title: Tutorial A
weight: 1
---
Content""")
        (grandchild2_dir / "page.md").write_text("Content")

        # Discover content
        discovery = ContentDiscovery(content_dir)
        sections, pages = discovery.discover()

        # Find the docs section
        docs_section = sections[0]

        # Child sections should be sorted
        assert len(docs_section.subsections) >= 2

        # Find beginner and advanced sections
        beginner_section = next((s for s in docs_section.subsections if s.name == "beginner"), None)
        advanced_section = next((s for s in docs_section.subsections if s.name == "advanced"), None)

        assert beginner_section is not None, "beginner section should exist"
        assert advanced_section is not None, "advanced section should exist"

        # Beginner should come before advanced (weight 1 < weight 100)
        beginner_idx = docs_section.subsections.index(beginner_section)
        advanced_idx = docs_section.subsections.index(advanced_section)
        assert beginner_idx < advanced_idx, "beginner(weight=1) should come before advanced(weight=100)"

        # Grandchild sections should be sorted within beginner
        assert len(beginner_section.subsections) == 2
        assert beginner_section.subsections[0].metadata["weight"] == 1   # tutorial-a
        assert beginner_section.subsections[1].metadata["weight"] == 50  # tutorial-z

    def test_discover_handles_missing_weights(self, tmp_path):
        """Pages/sections without weights default to 0 and sort by title."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        section_dir = content_dir / "docs"
        section_dir.mkdir()

        # Create pages - some with weights, some without
        (section_dir / "weighted.md").write_text("""---
title: Weighted Page
weight: 10
---
Content""")

        (section_dir / "zebra.md").write_text("""---
title: Zebra (No Weight)
---
Content""")

        (section_dir / "alpha.md").write_text("""---
title: Alpha (No Weight)
---
Content""")

        # Discover content
        discovery = ContentDiscovery(content_dir)
        sections, pages = discovery.discover()

        docs_section = sections[0]

        # Should be sorted: Alpha(0), Zebra(0), Weighted(10)
        assert len(docs_section.pages) == 3
        assert "Alpha" in docs_section.pages[0].title
        assert "Zebra" in docs_section.pages[1].title
        assert "Weighted" in docs_section.pages[2].title

    def test_discover_empty_section_no_error(self, tmp_path):
        """Empty sections don't cause sorting errors."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        section_dir = content_dir / "docs"
        section_dir.mkdir()
        (section_dir / "_index.md").write_text("""---
title: Docs
---
Empty section""")

        # Discover content (should not raise error)
        discovery = ContentDiscovery(content_dir)
        sections, pages = discovery.discover()

        # Should have the section even though it's empty
        assert len(sections) == 1
        assert sections[0].name == "docs"
        assert len(sections[0].pages) == 1  # Just the index page
        assert len(sections[0].subsections) == 0

    def test_discover_preserves_index_pages(self, tmp_path):
        """Index pages are included in sorted pages list."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        section_dir = content_dir / "docs"
        section_dir.mkdir()

        # Create index page with weight
        (section_dir / "_index.md").write_text("""---
title: Documentation Index
weight: 5
---
Index content""")

        # Create regular pages
        (section_dir / "page1.md").write_text("""---
title: Page 1
weight: 1
---
Content""")

        (section_dir / "page2.md").write_text("""---
title: Page 2
weight: 10
---
Content""")

        # Discover content
        discovery = ContentDiscovery(content_dir)
        sections, pages = discovery.discover()

        docs_section = sections[0]

        # Should have all pages including index, sorted by weight
        assert len(docs_section.pages) == 3
        assert docs_section.pages[0].metadata["weight"] == 1   # page1
        assert docs_section.pages[1].metadata["weight"] == 5   # _index
        assert docs_section.pages[2].metadata["weight"] == 10  # page2


class TestContentDiscoverySortingIntegration:
    """Integration tests for sorting across multiple scenarios."""

    def test_realistic_docs_structure(self, tmp_path):
        """Test realistic documentation structure with mixed weights."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        docs_dir = content_dir / "docs"
        docs_dir.mkdir()

        # Getting Started section (should be first)
        gs_dir = docs_dir / "getting-started"
        gs_dir.mkdir()
        (gs_dir / "_index.md").write_text("""---
title: Getting Started
weight: 1
---
Content""")
        (gs_dir / "installation.md").write_text("""---
title: Installation
weight: 1
---
Content""")
        (gs_dir / "quickstart.md").write_text("""---
title: Quick Start
weight: 2
---
Content""")

        # Advanced section (should be last)
        adv_dir = docs_dir / "advanced"
        adv_dir.mkdir()
        (adv_dir / "_index.md").write_text("""---
title: Advanced Topics
weight: 100
---
Content""")
        (adv_dir / "performance.md").write_text("""---
title: Performance
weight: 1
---
Content""")

        # Guides section (no weight - defaults to 0, but alphabetically after advanced)
        guides_dir = docs_dir / "guides"
        guides_dir.mkdir()
        (guides_dir / "_index.md").write_text("""---
title: Guides
---
Content""")
        (guides_dir / "guide1.md").write_text("Content")

        # Discover content
        discovery = ContentDiscovery(content_dir)
        sections, pages = discovery.discover()

        docs_section = sections[0]

        # Subsections should be sorted correctly
        assert len(docs_section.subsections) == 3

        # guides(0), getting-started(1), advanced(100)
        assert docs_section.subsections[0].name == "guides"
        assert docs_section.subsections[1].name == "getting-started"
        assert docs_section.subsections[2].name == "advanced"

        # Pages within getting-started should be sorted
        gs_section = docs_section.subsections[1]
        # _index(1), installation(1), quickstart(2)
        # When weights are equal, sorted by title
        assert len(gs_section.pages) == 3

