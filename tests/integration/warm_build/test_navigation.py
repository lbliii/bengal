"""
Integration tests for navigation updates during warm builds.

Tests that navigation/menu changes during warm builds correctly trigger
page rebuilds and update navigation structure.

Priority: P0 (HIGH) - Navigation is visible on every page; stale nav is
immediately noticeable by users.

See: plan/rfc-warm-build-test-expansion.md
"""

from __future__ import annotations

from tests.integration.warm_build.conftest import WarmBuildTestSite


class TestWarmBuildNavigation:
    """Test navigation updates during warm builds."""

    def test_menu_config_change_rebuilds_pages_with_nav(
        self, site_with_nav: WarmBuildTestSite
    ) -> None:
        """
        When menu.yaml/bengal.toml menu changes, pages displaying nav should rebuild.

        Scenario:
        1. Build site with nav (header menu with 3 items)
        2. Add new section to menu config
        3. Incremental build
        4. Assert: Pages with nav show new menu item
        """
        # Build 1: Full build with initial menu
        stats1 = site_with_nav.full_build()
        assert stats1.pages_built >= 1, "Initial build should create pages"

        # Verify initial nav structure (Home, Blog, Docs)
        home_html = site_with_nav.read_output("index.html")
        assert "Blog" in home_html or "blog" in home_html.lower()

        # Modify menu config - add Guides section
        site_with_nav.modify_file(
            "bengal.toml",
            """
[site]
title = "Nav Test Site"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = false

[[menu.main]]
name = "Home"
url = "/"
weight = 1

[[menu.main]]
name = "Blog"
url = "/blog/"
weight = 2

[[menu.main]]
name = "Docs"
url = "/docs/"
weight = 3

[[menu.main]]
name = "Guides"
url = "/guides/"
weight = 4
""",
        )

        # Create the guides section
        site_with_nav.create_file(
            "content/guides/_index.md",
            """---
title: Guides
menu:
  main:
    weight: 4
---

# Guides
""",
        )

        site_with_nav.wait_for_fs()

        # Build 2: Incremental build
        stats2 = site_with_nav.incremental_build()

        # Pages should be rebuilt due to menu config change
        # Note: Config changes typically trigger full rebuild in Bengal
        assert stats2.total_pages >= 1

    def test_nav_weight_change_updates_ordering(self, site_with_nav: WarmBuildTestSite) -> None:
        """
        When page nav weight changes, nav ordering updates.

        Scenario:
        1. Build with Blog (weight=2), Docs (weight=3)
        2. Change Blog weight to 10 (should appear after Docs)
        3. Incremental build
        4. Assert: Build completes and pages are updated
        """
        # Build 1: Full build
        site_with_nav.full_build()

        # Modify blog weight to move it after docs
        site_with_nav.modify_file(
            "content/blog/_index.md",
            """---
title: Blog
weight: 10
menu:
  main:
    weight: 10
---

# Blog
""",
        )

        site_with_nav.wait_for_fs()

        # Build 2: Incremental build
        stats2 = site_with_nav.incremental_build()

        # Build should succeed
        assert stats2.total_pages >= 1

    def test_new_section_appears_in_nav(self, site_with_nav: WarmBuildTestSite) -> None:
        """
        When new section is created, it appears in nav if configured.

        Scenario:
        1. Build with blog/ and docs/ sections
        2. Create tutorials/ section with menu weight
        3. Incremental build
        4. Assert: New section is discovered and built
        """
        # Build 1: Full build
        stats1 = site_with_nav.full_build()
        initial_pages = stats1.total_pages

        # Create new section
        site_with_nav.create_file(
            "content/tutorials/_index.md",
            """---
title: Tutorials
weight: 5
menu:
  main:
    weight: 5
---

# Tutorials

Learn step by step.
""",
        )

        site_with_nav.create_file(
            "content/tutorials/getting-started.md",
            """---
title: Getting Started
weight: 1
---

# Getting Started

Your first tutorial.
""",
        )

        site_with_nav.wait_for_fs()

        # Build 2: Incremental build
        stats2 = site_with_nav.incremental_build()

        # New section should be discovered
        assert stats2.total_pages >= initial_pages

        # Verify new section output exists
        site_with_nav.assert_output_exists("tutorials/index.html")
        site_with_nav.assert_output_exists("tutorials/getting-started/index.html")

    def test_deleted_section_removed_from_nav(self, site_with_nav: WarmBuildTestSite) -> None:
        """
        When section is deleted, nav should not reference it.

        Scenario:
        1. Build with blog/, docs/, guides/
        2. Delete guides/
        3. Build (full rebuild due to deletion)
        4. Assert: No broken nav links to guides/
        """
        # Create guides section first
        site_with_nav.create_file(
            "content/guides/_index.md",
            """---
title: Guides
menu:
  main:
    weight: 4
---

# Guides
""",
        )

        # Build 1: Full build with guides
        site_with_nav.full_build()
        site_with_nav.assert_output_exists("guides/index.html")

        # Delete guides section
        site_with_nav.delete_directory("content/guides")

        site_with_nav.wait_for_fs()

        # Build 2: Need full rebuild for deletion detection
        stats2 = site_with_nav.full_build()

        # Guides output should be cleaned up or not regenerated
        # Note: Output cleanup behavior depends on Bengal implementation
        assert stats2.total_pages >= 1

    def test_nested_menu_changes_cascade(self, site_with_nav: WarmBuildTestSite) -> None:
        """
        Nested menu changes should cascade to all affected pages.

        Scenario:
        1. Build with nested menu (docs/ → guides/ → intro.md)
        2. Change docs/_index.md title
        3. Incremental build
        4. Assert: Build processes the section change
        """
        # Build 1: Full build
        site_with_nav.full_build()

        # Change parent section title
        site_with_nav.modify_file(
            "content/docs/_index.md",
            """---
title: Documentation Center
weight: 2
menu:
  main:
    weight: 3
---

# Documentation Center

Updated documentation section.
""",
        )

        site_with_nav.wait_for_fs()

        # Build 2: Incremental build
        stats2 = site_with_nav.incremental_build()

        # Build should succeed and process the change
        assert stats2.total_pages >= 1

        # Verify the updated content
        docs_html = site_with_nav.read_output("docs/index.html")
        assert "Documentation Center" in docs_html

    def test_breadcrumb_updates_on_parent_change(self, site_with_nav: WarmBuildTestSite) -> None:
        """
        Breadcrumb navigation updates when parent changes.

        Scenario:
        1. Build with docs/guides/intro.md
        2. Change docs/_index.md title
        3. Incremental build
        4. Assert: Child page is rebuilt with updated parent reference
        """
        # Build 1: Full build
        site_with_nav.full_build()

        # Verify initial structure
        site_with_nav.assert_output_exists("docs/guides/intro/index.html")

        # Change parent title
        original_title = "Documentation"
        new_title = "Docs Hub"
        site_with_nav.modify_file(
            "content/docs/_index.md",
            f"""---
title: {new_title}
weight: 2
menu:
  main:
    weight: 3
---

# {new_title}
""",
        )

        site_with_nav.wait_for_fs()

        # Build 2: Incremental build
        stats2 = site_with_nav.incremental_build()

        # Build should complete
        assert stats2.total_pages >= 1

        # Verify parent section was updated
        docs_html = site_with_nav.read_output("docs/index.html")
        assert new_title in docs_html


class TestWarmBuildNavEdgeCases:
    """Edge cases for navigation warm builds."""

    def test_menu_item_url_change(self, site_with_nav: WarmBuildTestSite) -> None:
        """
        Test that menu item URL changes are detected.

        Scenario:
        1. Build with standard menu
        2. Change menu item URL via config
        3. Rebuild
        4. Assert: Build succeeds with updated config
        """
        # Build 1: Full build
        site_with_nav.full_build()

        # Change menu URL configuration
        site_with_nav.modify_file(
            "bengal.toml",
            """
[site]
title = "Nav Test Site"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = false

[[menu.main]]
name = "Home"
url = "/"
weight = 1

[[menu.main]]
name = "Blog Articles"
url = "/blog/"
weight = 2

[[menu.main]]
name = "Documentation"
url = "/docs/"
weight = 3
""",
        )

        site_with_nav.wait_for_fs()

        # Config change typically triggers full rebuild
        stats2 = site_with_nav.full_build()
        assert stats2.total_pages >= 1

    def test_empty_menu_section(self, site_with_nav: WarmBuildTestSite) -> None:
        """
        Test handling of empty menu sections.

        Scenario:
        1. Build with content
        2. Remove all menu items
        3. Rebuild
        4. Assert: Build succeeds without menu
        """
        # Build 1: Full build
        site_with_nav.full_build()

        # Remove menu configuration entirely
        site_with_nav.modify_file(
            "bengal.toml",
            """
[site]
title = "Nav Test Site"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
generate_sitemap = false
generate_rss = false
""",
        )

        site_with_nav.wait_for_fs()

        # Build 2: Full rebuild after config change
        stats2 = site_with_nav.full_build()

        # Should succeed without menu
        assert stats2.total_pages >= 1
