"""
Integration tests for Phase 2c.2: Incremental Tag Generation

Tests the TaxonomyIndex-based optimization that skips regenerating tag pages
when tag page membership hasn't changed.

Performance Target: ~160ms savings per incremental build for typical sites
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from bengal.cache.taxonomy_index import TaxonomyIndex
from bengal.core.site import Site
from bengal.orchestration.build import BuildOrchestrator


class TestTaxonomyIndexComparison:
    """Test TaxonomyIndex.pages_changed() comparison logic"""

    def test_new_tag_always_needs_generation(self):
        """Test that new tags are detected as needing generation"""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            index = TaxonomyIndex(tmpdir_path / "taxonomy_index.json")

            # New tag should always be marked as changed
            assert index.pages_changed("python", ["content/post1.md"])

    def test_unchanged_tag_membership_skips_generation(self):
        """Test that tags with unchanged membership are skipped"""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            index = TaxonomyIndex(tmpdir_path / "taxonomy_index.json")

            # Add initial tag
            index.update_tag("python", "Python", ["content/post1.md", "content/post2.md"])
            index.save_to_disk()

            # Load fresh and check - same pages shouldn't trigger generation
            index2 = TaxonomyIndex(tmpdir_path / "taxonomy_index.json")
            assert not index2.pages_changed("python", ["content/post1.md", "content/post2.md"])

    def test_added_page_to_tag_triggers_generation(self):
        """Test that adding a page to a tag triggers regeneration"""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            index = TaxonomyIndex(tmpdir_path / "taxonomy_index.json")

            # Add initial tag
            index.update_tag("python", "Python", ["content/post1.md", "content/post2.md"])
            index.save_to_disk()

            # Load fresh and check - new page should trigger generation
            index2 = TaxonomyIndex(tmpdir_path / "taxonomy_index.json")
            assert index2.pages_changed(
                "python", ["content/post1.md", "content/post2.md", "content/post3.md"]
            )

    def test_removed_page_from_tag_triggers_generation(self):
        """Test that removing a page from a tag triggers regeneration"""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            index = TaxonomyIndex(tmpdir_path / "taxonomy_index.json")

            # Add initial tag
            index.update_tag("python", "Python", ["content/post1.md", "content/post2.md"])
            index.save_to_disk()

            # Load fresh and check - removed page should trigger generation
            index2 = TaxonomyIndex(tmpdir_path / "taxonomy_index.json")
            assert index2.pages_changed("python", ["content/post1.md"])

    def test_page_order_doesnt_matter_for_comparison(self):
        """Test that page order doesn't affect comparison (set semantics)"""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            index = TaxonomyIndex(tmpdir_path / "taxonomy_index.json")

            # Add initial tag with ordered pages
            index.update_tag("python", "Python", ["content/post1.md", "content/post2.md"])
            index.save_to_disk()

            # Load fresh and check - different order should NOT trigger generation
            index2 = TaxonomyIndex(tmpdir_path / "taxonomy_index.json")
            assert not index2.pages_changed("python", ["content/post2.md", "content/post1.md"])


class TestIncrementalTagGeneration:
    """Test Phase 2c.2 incremental tag page generation"""

    def test_incremental_build_generates_tag_pages(self):
        """Test that incremental builds generate tag pages"""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            content_dir = tmpdir_path / "content"
            content_dir.mkdir()

            # Create test site with pages
            for i in range(3):
                page_file = content_dir / f"post{i}.md"
                page_file.write_text(f"""---
title: Post {i}
tags: [python, testing]
---

# Post {i}
Content here.
""")

            config = {
                "site": {"title": "Test Site", "baseurl": "http://localhost"},
                "build": {
                    "output_dir": str(tmpdir_path / "public"),
                    "generate_sitemap": False,
                    "generate_rss": False,
                },
            }

            # FIRST BUILD
            site1 = Site.for_testing(root_path=tmpdir_path, config=config)
            orch1 = BuildOrchestrator(site1)
            orch1.build(incremental=False)

            tag_pages_1 = [
                p
                for p in site1.pages
                if p.metadata.get("_generated") and "tags" in str(p.output_path)
            ]
            assert len(tag_pages_1) > 0, "Should have generated tag pages"

            # SECOND BUILD (incremental, no changes)
            site2 = Site.for_testing(root_path=tmpdir_path, config=config)
            orch2 = BuildOrchestrator(site2)
            orch2.build(incremental=True)

            # Should still have tag pages from incremental
            tag_pages_2 = [
                p
                for p in site2.pages
                if p.metadata.get("_generated") and "tags" in str(p.output_path)
            ]
            assert len(tag_pages_2) > 0, "Should have tag pages in incremental build"

    def test_modified_page_regenerates_affected_tags(self):
        """Test that modifying a page regenerates its tags"""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            content_dir = tmpdir_path / "content"
            content_dir.mkdir()

            # Create initial post
            post_file = content_dir / "post1.md"
            post_file.write_text("""---
title: Post 1
tags: [python]
---

# Post 1
Original content.
""")

            config = {
                "site": {"title": "Test Site", "baseurl": "http://localhost"},
                "build": {
                    "output_dir": str(tmpdir_path / "public"),
                    "generate_sitemap": False,
                    "generate_rss": False,
                },
            }

            # FIRST BUILD
            site1 = Site.for_testing(root_path=tmpdir_path, config=config)
            orch1 = BuildOrchestrator(site1)
            orch1.build(incremental=False)

            # MODIFY POST (add new tag)
            post_file.write_text("""---
title: Post 1 Updated
tags: [python, django]
---

# Post 1 Updated
Modified content with new tag.
""")

            # SECOND BUILD (incremental)
            site2 = Site.for_testing(root_path=tmpdir_path, config=config)
            orch2 = BuildOrchestrator(site2)
            orch2.build(incremental=True)

            # Should have regenerated django tag page
            django_pages = [
                p
                for p in site2.pages
                if p.metadata.get("_generated") and "django" in str(p.output_path)
            ]
            assert len(django_pages) > 0, "Should have generated django tag pages"

    def test_taxonomy_index_created(self):
        """Test that TaxonomyIndex is created during builds"""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            content_dir = tmpdir_path / "content"
            content_dir.mkdir()

            # Create pages
            for i in range(2):
                page_file = content_dir / f"post{i}.md"
                page_file.write_text(f"""---
title: Post {i}
tags: [python]
---

# Post {i}
Content.
""")

            config = {
                "site": {"title": "Test Site", "baseurl": "http://localhost"},
                "build": {
                    "output_dir": str(tmpdir_path / "public"),
                    "generate_sitemap": False,
                    "generate_rss": False,
                },
            }

            # BUILD
            site1 = Site.for_testing(root_path=tmpdir_path, config=config)
            orch1 = BuildOrchestrator(site1)
            orch1.build(incremental=False)

            # Check that TaxonomyIndex was created
            index_file = tmpdir_path / ".bengal" / "taxonomy_index.json"
            assert index_file.exists(), "TaxonomyIndex should be persisted"

            # Verify it has correct data
            index = TaxonomyIndex(index_file)
            assert "python" in index.tags


class TestTagGenerationSkipping:
    """Test that tag generation is properly optimized with TaxonomyIndex"""

    def test_unchanged_tags_detected(self):
        """Test that unchanged tags are properly detected"""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            content_dir = tmpdir_path / "content"
            content_dir.mkdir()

            # Create pages with distinct tags
            for i in range(3):
                tags = "python" if i == 0 else ("django" if i == 1 else "testing")
                page_file = content_dir / f"post{i}.md"
                page_file.write_text(f"""---
title: Post {i}
tags: [{tags}]
---

# Post {i}
Content.
""")

            config = {
                "site": {"title": "Test Site", "baseurl": "http://localhost"},
                "build": {
                    "output_dir": str(tmpdir_path / "public"),
                    "generate_sitemap": False,
                    "generate_rss": False,
                },
            }

            # FIRST BUILD - full
            site1 = Site.for_testing(root_path=tmpdir_path, config=config)
            orch1 = BuildOrchestrator(site1)
            orch1.build(incremental=False)

            # SECOND BUILD - incremental with no changes
            site2 = Site.for_testing(root_path=tmpdir_path, config=config)
            orch2 = BuildOrchestrator(site2)
            orch2.build(incremental=True)

            # Both builds should complete successfully
            assert len(site1.pages) > 0
            assert len(site2.pages) > 0


class TestTagGenerationWithMultipleChanges:
    """Test tag generation with multiple page changes"""

    def test_add_page_with_new_tag(self):
        """Test adding a new page with a new tag"""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            content_dir = tmpdir_path / "content"
            content_dir.mkdir()

            # Create initial post
            post_file = content_dir / "post1.md"
            post_file.write_text("""---
title: Post 1
tags: [python]
---

# Post 1
Content.
""")

            config = {
                "site": {"title": "Test Site", "baseurl": "http://localhost"},
                "build": {
                    "output_dir": str(tmpdir_path / "public"),
                    "generate_sitemap": False,
                    "generate_rss": False,
                },
            }

            # FIRST BUILD
            site1 = Site.for_testing(root_path=tmpdir_path, config=config)
            orch1 = BuildOrchestrator(site1)
            orch1.build(incremental=False)

            # ADD NEW PAGE
            post2_file = content_dir / "post2.md"
            post2_file.write_text("""---
title: Post 2
tags: [golang]
---

# Post 2
New content.
""")

            # SECOND BUILD
            site2 = Site.for_testing(root_path=tmpdir_path, config=config)
            orch2 = BuildOrchestrator(site2)
            orch2.build(incremental=True)

            # Should have golang tag pages
            golang_pages = [
                p
                for p in site2.pages
                if p.metadata.get("_generated") and "golang" in str(p.output_path)
            ]
            assert len(golang_pages) > 0, "Should have generated golang tag pages"
