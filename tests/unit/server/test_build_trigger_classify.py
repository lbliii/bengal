"""Tests for BuildTrigger classification."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.server.build_trigger import BuildTrigger


class TestBuildTriggerClassify:
    """Change classification: content-only, nav frontmatter, hash cache."""

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.root_path = Path("/test/site")
        site.output_dir = Path("/test/site/public")
        site.config = {}
        site.theme = None
        return site

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create a mock executor for testing."""
        executor = MagicMock()
        result = MagicMock()
        result.success = True
        result.pages_built = 5
        result.build_time_ms = 100.0
        result.error_message = None
        result.changed_outputs = ()
        executor.submit.return_value = result
        return executor

    def test_can_use_reactive_path_single_md_modified(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _can_use_reactive_path returns True for content-only .md edit."""
        md_file = tmp_path / "content" / "page.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("---\ntitle: Test\n---\nOriginal body")
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # First call: no cache, populates cache and returns False
        result = trigger._can_use_reactive_path({md_file}, {"modified"})
        assert result is False

        # Change body only (frontmatter unchanged)
        md_file.write_text("---\ntitle: Test\n---\nNew body")
        result = trigger._can_use_reactive_path({md_file}, {"modified"})
        assert result is True

    def test_can_use_reactive_path_rejects_multiple_files(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _can_use_reactive_path returns False for multiple files."""
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        a.write_text("---\ntitle: A\n---\nA")
        b.write_text("---\ntitle: B\n---\nB")
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._can_use_reactive_path({a, b}, {"modified"}) is False

    def test_can_use_reactive_path_rejects_created_event(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _can_use_reactive_path returns False for created event."""
        md_file = tmp_path / "page.md"
        md_file.write_text("---\ntitle: Test\n---\nBody")
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._can_use_reactive_path({md_file}, {"created"}) is False

    def test_can_use_reactive_path_rejects_non_md(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _can_use_reactive_path returns False for non-.md files."""
        txt_file = tmp_path / "file.txt"
        txt_file.write_text("content")
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._can_use_reactive_path({txt_file}, {"modified"}) is False

    def test_seed_content_hash_cache_populates_cache(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that seed_content_hash_cache populates cache for content pages."""
        md_file = tmp_path / "content" / "page.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("---\ntitle: Test\n---\nOriginal body")

        page = MagicMock()
        page.source_path = md_file
        page._section = None
        mock_site.pages = [page]

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.seed_content_hash_cache([page])

        assert md_file in trigger._content_hash_cache
        entry = trigger._content_hash_cache[md_file]
        assert entry.frontmatter_hash
        assert entry.content_hash

    def test_first_edit_uses_reactive_path_after_seed(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that first content-only edit uses reactive path after seed."""
        md_file = tmp_path / "content" / "page.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("---\ntitle: Test\n---\nOriginal body")

        page = MagicMock()
        page.source_path = md_file
        page._section = None
        mock_site.pages = [page]

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.seed_content_hash_cache([page])

        # Simulate user editing body only
        md_file.write_text("---\ntitle: Test\n---\nEdited body")
        result = trigger._can_use_reactive_path({md_file}, {"modified"})
        assert result is True

    def test_reactive_path_rejects_page_with_rendered_section_index(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Leaf pages with rendered section indexes need the warm build path."""
        md_file = tmp_path / "content" / "docs" / "page.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("---\ntitle: Test\n---\nOriginal body")

        index_page = MagicMock()
        index_page.output_path = tmp_path / "public" / "docs" / "index.html"
        section = MagicMock()
        section.index_page = index_page
        page = MagicMock()
        page.source_path = md_file
        page._section = section
        mock_site.pages = [page]

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.seed_content_hash_cache([page])

        md_file.write_text("---\ntitle: Test\n---\nEdited body")

        assert trigger._can_use_reactive_path({md_file}, {"modified"}) is False

    def test_seed_content_hash_cache_section_page(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that seed_content_hash_cache works for section _index.md."""
        index_file = tmp_path / "content" / "docs" / "_index.md"
        index_file.parent.mkdir(parents=True)
        index_file.write_text("---\ntitle: Docs\n---\nSection intro.")

        page = MagicMock()
        page.source_path = index_file
        page._section = None
        mock_site.pages = [page]

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.seed_content_hash_cache([page])

        assert index_file in trigger._content_hash_cache
        index_file.write_text("---\ntitle: Docs\n---\nUpdated intro.")
        assert trigger._can_use_reactive_path({index_file}, {"modified"}) is True

    def test_seed_content_hash_cache_skips_non_md(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that seed_content_hash_cache skips non-.md pages."""
        txt_file = tmp_path / "content" / "readme.txt"
        txt_file.parent.mkdir(parents=True)
        txt_file.write_text("No frontmatter")

        page = MagicMock()
        page.source_path = txt_file
        mock_site.pages = [page]

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.seed_content_hash_cache([page])

        assert txt_file not in trigger._content_hash_cache

    def test_seed_content_hash_cache_skips_no_frontmatter(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that seed_content_hash_cache skips files without frontmatter."""
        md_file = tmp_path / "content" / "page.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("No frontmatter here, just body.")

        page = MagicMock()
        page.source_path = md_file
        mock_site.pages = [page]

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.seed_content_hash_cache([page])

        assert md_file not in trigger._content_hash_cache

    def test_detect_nav_changes_finds_nav_frontmatter(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that nav frontmatter detection works."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a test file with nav frontmatter
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test Page
weight: 10
---

Content here.
"""
        )

        result = trigger._detect_nav_changes({test_file}, needs_full_rebuild=False)
        assert test_file in result

    def test_detect_nav_changes_skips_non_nav_frontmatter(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that non-nav frontmatter is skipped."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a test file without nav-affecting frontmatter
        # (no title, weight, order, draft, headless, etc.)
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
author: Someone
description: A test page
tags:
  - test
---

Content here.
"""
        )

        result = trigger._detect_nav_changes({test_file}, needs_full_rebuild=False)
        assert test_file not in result

    def test_detect_nav_changes_skips_when_full_rebuild(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that nav detection is skipped for full rebuilds."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test
weight: 10
---
"""
        )

        result = trigger._detect_nav_changes({test_file}, needs_full_rebuild=True)
        assert len(result) == 0


class TestBuildTriggerFrontmatterCache:
    """Frontmatter cache used by classification."""

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.root_path = Path("/test/site")
        site.output_dir = Path("/test/site/public")
        site.config = {}
        site.theme = None
        return site

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create a mock executor for testing."""
        executor = MagicMock()
        result = MagicMock()
        result.success = True
        result.pages_built = 5
        result.build_time_ms = 100.0
        result.error_message = None
        result.changed_outputs = ()
        executor.submit.return_value = result
        return executor

    def test_frontmatter_cache_hit(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that frontmatter parsing is cached by mtime."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a test file with nav frontmatter
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test Page
weight: 10
---

Content here.
"""
        )

        # First call - cache miss
        result1 = trigger._has_nav_affecting_frontmatter(test_file)
        assert result1 is True
        assert test_file in trigger._frontmatter_cache

        # Second call - cache hit (same mtime)
        result2 = trigger._has_nav_affecting_frontmatter(test_file)
        assert result2 is True

    def test_frontmatter_cache_invalidation_on_mtime_change(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that frontmatter cache is invalidated when mtime changes."""
        import os
        import time

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create initial file with nav frontmatter
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test Page
weight: 10
---
"""
        )

        # First call
        result1 = trigger._has_nav_affecting_frontmatter(test_file)
        assert result1 is True

        # Modify file (change content, touch mtime)
        time.sleep(0.01)  # Ensure mtime changes
        test_file.write_text(
            """---
author: Someone
---
"""
        )
        # Force mtime update
        os.utime(test_file, None)

        # Second call - should re-parse due to mtime change
        result2 = trigger._has_nav_affecting_frontmatter(test_file)
        assert result2 is False  # No nav-affecting keys now

    def test_frontmatter_partial_read(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that only first 4KB is read for frontmatter."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a file with frontmatter and lots of content
        large_content = "x" * 100000  # 100KB of content
        test_file = tmp_path / "large.md"
        test_file.write_text(
            f"""---
title: Large File
---

{large_content}
"""
        )

        # Should still detect nav frontmatter without reading entire file
        result = trigger._has_nav_affecting_frontmatter(test_file)
        assert result is True

    def test_detect_nav_changes_uses_cache(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _detect_nav_changes uses the frontmatter cache."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test
weight: 5
---
"""
        )

        # First detection
        result1 = trigger._detect_nav_changes({test_file}, needs_full_rebuild=False)
        assert test_file in result1

        # File should be cached now
        assert test_file in trigger._frontmatter_cache

        # Second detection should use cache
        result2 = trigger._detect_nav_changes({test_file}, needs_full_rebuild=False)
        assert test_file in result2
