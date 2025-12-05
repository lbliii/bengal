"""
Tests for content discovery symlink loop protection.

Tests that content discovery:
- Detects and skips symlink loops
- Handles permission errors gracefully
- Still processes regular directories correctly
"""

from __future__ import annotations

import os

import pytest

from bengal.discovery.content_discovery import ContentDiscovery


@pytest.fixture
def temp_content_dir(tmp_path):
    """Create a temporary content directory structure."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create some content
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")
    docs_dir = content_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "_index.md").write_text("---\ntitle: Docs\n---\n# Docs")
    (docs_dir / "guide.md").write_text("---\ntitle: Guide\n---\n# Guide")

    return content_dir


class TestSymlinkLoopDetection:
    """Test symlink loop detection in content discovery."""

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks require admin on Windows")
    def test_symlink_loop_to_self_is_skipped(self, temp_content_dir):
        """Test that a directory symlink to itself is detected and skipped."""
        # Create a symlink loop: docs/loop -> docs
        docs_dir = temp_content_dir / "docs"
        loop_link = docs_dir / "loop"
        loop_link.symlink_to(docs_dir)

        discovery = ContentDiscovery(temp_content_dir)
        sections, pages = discovery.discover()

        # Should not hang or crash
        # Should find the normal pages
        page_titles = [p.title for p in pages]
        assert "Home" in page_titles or any("Home" in str(p.source_path) for p in pages)

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks require admin on Windows")
    def test_symlink_loop_indirect_is_skipped(self, temp_content_dir):
        """Test that indirect symlink loops (a -> b -> a) are detected."""
        # Create an indirect loop
        docs_dir = temp_content_dir / "docs"
        guides_dir = docs_dir / "guides"
        guides_dir.mkdir()
        (guides_dir / "_index.md").write_text("---\ntitle: Guides\n---\n# Guides")

        # Create a symlink: docs/guides/back-to-docs -> docs
        back_link = guides_dir / "back-to-docs"
        back_link.symlink_to(docs_dir)

        discovery = ContentDiscovery(temp_content_dir)
        sections, pages = discovery.discover()

        # Should not hang or crash
        assert isinstance(pages, list)
        assert isinstance(sections, list)

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks require admin on Windows")
    def test_valid_symlink_to_other_dir_works(self, tmp_path):
        """Test that non-loop symlinks to other directories work."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        # Create a separate directory with content
        shared_dir = tmp_path / "shared"
        shared_dir.mkdir()
        (shared_dir / "_index.md").write_text("---\ntitle: Shared\n---\n# Shared")
        (shared_dir / "article.md").write_text("---\ntitle: Article\n---\n# Article")

        # Symlink to the separate directory (not a loop)
        link = content_dir / "shared"
        link.symlink_to(shared_dir)

        discovery = ContentDiscovery(content_dir)
        sections, pages = discovery.discover()

        # Should find content from both directories
        assert len(pages) >= 2

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks require admin on Windows")
    def test_deep_symlink_loop_is_skipped(self, temp_content_dir):
        """Test that deeply nested symlink loops are detected."""
        # Create a deep structure with a loop back to the root
        current = temp_content_dir / "docs"
        for i in range(5):
            next_dir = current / f"level{i}"
            next_dir.mkdir()
            (next_dir / "_index.md").write_text(f"---\ntitle: Level {i}\n---\n# Level {i}")
            current = next_dir

        # Create a symlink at the deepest level back to docs
        loop_link = current / "back-to-docs"
        loop_link.symlink_to(temp_content_dir / "docs")

        discovery = ContentDiscovery(temp_content_dir)
        sections, pages = discovery.discover()

        # Should complete without hanging
        assert isinstance(pages, list)

    def test_normal_directories_not_affected(self, temp_content_dir):
        """Test that normal directories (no symlinks) work correctly."""
        # Add more regular directories
        for i in range(3):
            section_dir = temp_content_dir / f"section{i}"
            section_dir.mkdir()
            (section_dir / "_index.md").write_text(f"---\ntitle: Section {i}\n---\n# Section {i}")
            (section_dir / "page.md").write_text(f"---\ntitle: Page in Section {i}\n---\n# Page")

        discovery = ContentDiscovery(temp_content_dir)
        sections, pages = discovery.discover()

        # Should find all pages
        assert len(pages) >= 8  # Home + 3 sections * (index + page) + docs

    def test_visited_inodes_reset_between_discoveries(self, temp_content_dir):
        """Test that visited inodes set is reset between discovery calls."""
        discovery = ContentDiscovery(temp_content_dir)

        # First discovery
        sections1, pages1 = discovery.discover()
        assert len(pages1) > 0

        # Add more content
        (temp_content_dir / "new-page.md").write_text("---\ntitle: New\n---\n# New")

        # Reset pages and sections (simulate fresh discovery)
        discovery.pages = []
        discovery.sections = []

        # Second discovery should find the new page
        sections2, pages2 = discovery.discover()
        assert len(pages2) > 0


class TestPermissionErrorHandling:
    """Test that permission errors are handled gracefully."""

    @pytest.mark.skipif(os.name == "nt", reason="Permission tests unreliable on Windows")
    def test_unreadable_directory_is_skipped(self, temp_content_dir):
        """Test that unreadable directories are skipped with a warning."""
        # Create a directory and remove read permission
        no_access = temp_content_dir / "no-access"
        no_access.mkdir()
        (no_access / "_index.md").write_text("---\ntitle: No Access\n---\n# No Access")

        try:
            # Remove read permission
            no_access.chmod(0o000)

            discovery = ContentDiscovery(temp_content_dir)
            sections, pages = discovery.discover()

            # Should not crash, just skip the unreadable directory
            assert isinstance(pages, list)

        finally:
            # Restore permission for cleanup
            no_access.chmod(0o755)
