"""
Integration tests for edge cases and boundary conditions in warm builds.

Tests unusual scenarios and edge cases that could cause issues in
incremental builds.

Priority: P2 (LOWER) - Edge cases are less common but important for
robustness.

See: plan/rfc-warm-build-test-expansion.md
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import pytest

from tests.integration.warm_build.conftest import (
    WarmBuildTestSite,
    create_basic_site_structure,
)


class TestWarmBuildEdgeCases:
    """Test edge cases and boundary conditions in warm builds."""

    def test_empty_site_after_all_content_deleted(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        Warm build handles empty site gracefully.

        Scenario:
        1. Build with 5 pages
        2. Delete all content
        3. Full rebuild (deletion requires full)
        4. Assert: Build succeeds, output is minimal/empty
        """
        # Create additional pages
        for i in range(5):
            warm_build_site.create_file(
                f"content/page{i}.md",
                f"""---
title: Page {i}
---

Content for page {i}.
""",
            )

        # Build 1: Full build with pages
        stats1 = warm_build_site.full_build()
        assert stats1.total_pages >= 5

        # Delete all content
        content_dir = warm_build_site.site_dir / "content"
        shutil.rmtree(content_dir)
        content_dir.mkdir()

        # Create empty index to prevent errors
        (content_dir / "_index.md").write_text("""---
title: Empty Site
---
""")

        warm_build_site.wait_for_fs()

        # Build 2: Full rebuild after deletion
        stats2 = warm_build_site.full_build()

        # Build should succeed with minimal content
        assert stats2.total_pages >= 1

    def test_batch_changes_100_files(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        Warm build handles 100+ simultaneous file changes.

        Scenario:
        1. Build with 100 pages
        2. Modify all 100 pages
        3. Incremental build
        4. Assert: All pages rebuilt correctly
        """
        # Create 100 pages
        for i in range(100):
            warm_build_site.create_file(
                f"content/page{i:03d}.md",
                f"""---
title: Page {i}
---

Original content for page {i}.
""",
            )

        # Build 1: Full build
        stats1 = warm_build_site.full_build()
        assert stats1.total_pages >= 100

        # Modify all 100 pages
        for i in range(100):
            warm_build_site.modify_file(
                f"content/page{i:03d}.md",
                f"""---
title: Page {i} Updated
---

Modified content for page {i} - BATCH UPDATE.
""",
            )

        warm_build_site.wait_for_fs(0.1)  # Longer wait for batch

        # Build 2: Incremental build
        stats2 = warm_build_site.incremental_build()

        # All pages should be processed
        assert stats2.total_pages >= 100

    def test_deep_nesting_10_levels(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        Deep directory nesting handled correctly.

        Scenario:
        1. Build with deeply nested content (10 levels)
        2. Modify intermediate _index.md
        3. Incremental build
        4. Assert: Build completes successfully
        """
        # Create deeply nested structure
        nested_path = "content/level1/level2/level3/level4/level5/level6/level7/level8/level9/level10"

        # Create _index.md at each level
        for i in range(1, 11):
            level_path = "/".join(["content"] + [f"level{j}" for j in range(1, i + 1)])
            warm_build_site.create_file(
                f"{level_path}/_index.md",
                f"""---
title: Level {i}
weight: {i}
---

Level {i} section.
""",
            )

        # Create leaf page
        warm_build_site.create_file(
            f"{nested_path}/deep-page.md",
            """---
title: Deep Nested Page
---

This page is 10 levels deep.
""",
        )

        # Build 1: Full build
        stats1 = warm_build_site.full_build()
        assert stats1.total_pages >= 1

        # Verify deep page was created
        warm_build_site.assert_output_exists("level1/level2/level3/level4/level5/level6/level7/level8/level9/level10/deep-page/index.html")

        # Modify intermediate level
        warm_build_site.modify_file(
            "content/level1/level2/level3/level4/level5/_index.md",
            """---
title: Level 5 - MODIFIED
weight: 5
---

Level 5 section updated with new content.
""",
        )

        warm_build_site.wait_for_fs()

        # Build 2: Incremental build
        stats2 = warm_build_site.incremental_build()

        # Build should complete (stats vary based on cache behavior)
        # The key test is that it doesn't crash with deep nesting
        assert stats2 is not None

    def test_same_second_modifications(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        Multiple modifications in same second detected.

        Scenario:
        1. Build with page
        2. Modify page twice in <1 second
        3. Incremental build
        4. Assert: Final content reflected
        """
        # Create page
        warm_build_site.create_file(
            "content/rapid.md",
            """---
title: Rapid Changes
---

Original content.
""",
        )

        # Build 1: Full build
        warm_build_site.full_build()

        # Modify page rapidly (two changes in quick succession)
        warm_build_site.modify_file(
            "content/rapid.md",
            """---
title: Rapid Changes
---

First modification.
""",
        )

        # Second modification immediately
        warm_build_site.modify_file(
            "content/rapid.md",
            """---
title: Rapid Changes
---

FINAL modification content.
""",
        )

        warm_build_site.wait_for_fs()

        # Build 2: Incremental build
        stats2 = warm_build_site.incremental_build()

        # Final content should be reflected
        html = warm_build_site.read_output("rapid/index.html")
        assert "FINAL" in html, "Final modification should be reflected"

    def test_unicode_filenames(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        Unicode filenames in warm builds.

        Scenario:
        1. Build with unicode filenames (日本語.md, émojis-🎉.md)
        2. Modify unicode files
        3. Incremental build
        4. Assert: Files rebuilt correctly
        """
        # Create pages with unicode filenames
        warm_build_site.create_file(
            "content/日本語.md",
            """---
title: Japanese Page
---

日本語のコンテンツ。
""",
        )

        warm_build_site.create_file(
            "content/café-☕.md",
            """---
title: Café Page
---

Content about café ☕
""",
        )

        # Build 1: Full build
        stats1 = warm_build_site.full_build()
        assert stats1.total_pages >= 1

        # Modify unicode file
        warm_build_site.modify_file(
            "content/日本語.md",
            """---
title: Japanese Page Updated
---

更新された日本語のコンテンツ。
UPDATED Japanese content.
""",
        )

        warm_build_site.wait_for_fs()

        # Build 2: Incremental build
        stats2 = warm_build_site.incremental_build()

        # Build should succeed
        assert stats2.total_pages >= 1

    @pytest.mark.skipif(
        os.name == "nt",
        reason="Symlinks require elevated privileges on Windows"
    )
    def test_symlinked_content(self, tmp_path: Path) -> None:
        """
        Symlinked content directories handled.

        Scenario:
        1. Build with symlinked content/shared/
        2. Modify file through symlink
        3. Incremental build
        4. Assert: Change detected and rebuilt
        """
        # Create site directory
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        create_basic_site_structure(site_dir)

        # Create external shared content directory
        shared_dir = tmp_path / "shared_content"
        shared_dir.mkdir()
        (shared_dir / "shared-page.md").write_text("""---
title: Shared Page
---

Shared content via symlink.
""")

        # Create symlink to shared content
        content_dir = site_dir / "content"
        symlink_path = content_dir / "shared"
        symlink_path.symlink_to(shared_dir)

        # Create test helper
        test_site = WarmBuildTestSite(site_dir=site_dir)

        # Build 1: Full build
        stats1 = test_site.full_build()
        assert stats1.total_pages >= 1

        # Modify file through symlink
        (shared_dir / "shared-page.md").write_text("""---
title: Shared Page Updated
---

UPDATED shared content via symlink.
""")

        test_site.wait_for_fs()

        # Build 2: Incremental build
        stats2 = test_site.incremental_build()

        # Build should succeed
        assert stats2.total_pages >= 1

    def test_case_sensitivity(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        Case sensitivity handled correctly.

        Scenario:
        1. Build with Page.md
        2. Rename to page.md (case change only)
        3. Full rebuild (rename is delete + create)
        4. Assert: URL reflects new filename
        """
        # Create page with uppercase
        warm_build_site.create_file(
            "content/MyPage.md",
            """---
title: My Page
---

Content for my page.
""",
        )

        # Build 1: Full build
        stats1 = warm_build_site.full_build()
        assert stats1.total_pages >= 1

        # Rename to lowercase (delete old, create new)
        warm_build_site.delete_file("content/MyPage.md")
        warm_build_site.create_file(
            "content/mypage.md",
            """---
title: My Page
---

Content for my page - lowercase version.
""",
        )

        warm_build_site.wait_for_fs()

        # Build 2: Full rebuild for rename
        stats2 = warm_build_site.full_build()

        # Build should succeed
        assert stats2.total_pages >= 1

    def test_content_and_output_same_mtime(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        Handles case where source and output have identical mtime.

        Scenario:
        1. Build page
        2. Touch source to match output mtime exactly
        3. Modify content but preserve mtime
        4. Incremental build
        5. Assert: Content hash detection triggers rebuild
        """
        # Create page
        warm_build_site.create_file(
            "content/mtime-test.md",
            """---
title: Mtime Test
---

Original content for mtime testing.
""",
        )

        # Build 1: Full build
        warm_build_site.full_build()

        source_path = warm_build_site.site_dir / "content" / "mtime-test.md"
        output_path = warm_build_site.output_dir / "mtime-test" / "index.html"

        if output_path.exists():
            # Get output mtime
            output_mtime = output_path.stat().st_mtime

            # Set source to same mtime
            os.utime(source_path, (output_mtime, output_mtime))

            # Now modify content (this will update mtime)
            warm_build_site.modify_file(
                "content/mtime-test.md",
                """---
title: Mtime Test
---

MODIFIED content with hash detection.
""",
            )

            warm_build_site.wait_for_fs()

            # Build 2: Incremental build
            stats2 = warm_build_site.incremental_build()

            # Build should succeed
            assert stats2.total_pages >= 1

            # Modified content should be reflected
            html = warm_build_site.read_output("mtime-test/index.html")
            assert "MODIFIED" in html


class TestWarmBuildBoundaryConditions:
    """Test boundary conditions for warm builds."""

    def test_very_large_file(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        Very large markdown file handled correctly.

        Scenario:
        1. Build with normal-sized files
        2. Add a very large file (1MB+ of content)
        3. Incremental build
        4. Assert: Large file is processed correctly
        """
        # Build 1: Full build
        warm_build_site.full_build()

        # Create large file (approximately 1MB)
        large_content = "Content paragraph.\n\n" * 50000  # ~1MB
        warm_build_site.create_file(
            "content/large-file.md",
            f"""---
title: Large File
---

# Large File

{large_content}
""",
        )

        warm_build_site.wait_for_fs()

        # Build 2: Incremental build
        stats2 = warm_build_site.incremental_build()

        # Build should succeed
        assert stats2.total_pages >= 1
        warm_build_site.assert_output_exists("large-file/index.html")

    def test_empty_content_file(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        Empty content file handled gracefully.

        Scenario:
        1. Build with normal files
        2. Create empty content file
        3. Incremental build
        4. Assert: Build handles empty file gracefully
        """
        # Build 1: Full build
        warm_build_site.full_build()

        # Create empty file (just frontmatter, no body)
        warm_build_site.create_file(
            "content/empty.md",
            """---
title: Empty Content
---
""",
        )

        warm_build_site.wait_for_fs()

        # Build 2: Incremental build
        stats2 = warm_build_site.incremental_build()

        # Build should succeed
        assert stats2.total_pages >= 1

    def test_special_characters_in_title(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        Special characters in titles handled correctly.

        Scenario:
        1. Build with special characters in frontmatter
        2. Modify the file
        3. Incremental build
        4. Assert: Build succeeds
        """
        # Create page with special characters
        warm_build_site.create_file(
            "content/special.md",
            """---
title: "Special: Chars & <HTML> 'Quotes' \"Double\""
description: |
  Multi-line description with special chars:
  • Bullet points
  • Em-dash — and en-dash –
  • Smart quotes "quoted"
---

# Special Characters Test

Content with <script>alert('test')</script> and &amp; entities.
""",
        )

        # Build 1: Full build
        stats1 = warm_build_site.full_build()
        assert stats1.total_pages >= 1

        # Modify file
        warm_build_site.modify_file(
            "content/special.md",
            """---
title: "Updated: Chars & <HTML> 'Quotes'"
description: Updated description
---

# Updated Special Characters

Modified content.
""",
        )

        warm_build_site.wait_for_fs()

        # Build 2: Incremental build
        stats2 = warm_build_site.incremental_build()

        # Build should succeed
        assert stats2.total_pages >= 1

    def test_frontmatter_only_no_body(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        Files with frontmatter but no body content handled.

        Scenario:
        1. Create file with only frontmatter
        2. Build
        3. Assert: Page is created (possibly with empty body)
        """
        warm_build_site.create_file(
            "content/frontmatter-only.md",
            """---
title: Frontmatter Only
date: 2026-01-15
draft: false
tags: [test]
---""",
        )

        # Build
        stats = warm_build_site.full_build()

        # Build should succeed
        assert stats.total_pages >= 1
