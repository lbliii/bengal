"""Tests for file tracking path resolution.

Ensures that should_bypass correctly handles path variations
(symlinks, ./ components, different representations of same file).

RFC: Theme hot reload path resolution fix
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.cache.build_cache.file_tracking import FileTrackingMixin


class MockFileTracking(FileTrackingMixin):
    """Mock class that uses FileTrackingMixin for testing."""

    def __init__(self) -> None:
        self.file_fingerprints: dict[str, dict] = {}


class TestShouldBypassPathResolution:
    """Tests for should_bypass path resolution handling."""

    @pytest.fixture
    def tracker(self) -> MockFileTracking:
        """Create a mock file tracker."""
        return MockFileTracking()

    @pytest.fixture
    def temp_file(self, tmp_path: Path) -> Path:
        """Create a temporary file for testing."""
        test_file = tmp_path / "test.css"
        test_file.write_text("/* test */")
        return test_file

    def test_exact_path_match(self, tracker: MockFileTracking, temp_file: Path) -> None:
        """Test that exact path matches are detected."""
        changed_sources = {temp_file}

        result = tracker.should_bypass(temp_file, changed_sources)

        assert result is True

    def test_resolved_path_match(self, tracker: MockFileTracking, temp_file: Path) -> None:
        """Test that resolved paths match even with different representations."""
        # Create a path with ./ component
        path_with_dot = temp_file.parent / "." / temp_file.name

        changed_sources = {temp_file}

        result = tracker.should_bypass(path_with_dot, changed_sources)

        assert result is True

    def test_symlink_path_match(self, tracker: MockFileTracking, tmp_path: Path) -> None:
        """Test that symlinked paths match their targets."""
        # Create a real file
        real_file = tmp_path / "real.css"
        real_file.write_text("/* real */")

        # Create a symlink to it
        symlink = tmp_path / "link.css"
        try:
            symlink.symlink_to(real_file)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        # Changed sources contains real file
        changed_sources = {real_file}

        # should_bypass with symlink should still match
        result = tracker.should_bypass(symlink, changed_sources)

        assert result is True

    def test_symlink_in_changed_sources(self, tracker: MockFileTracking, tmp_path: Path) -> None:
        """Test that real paths match when symlink is in changed_sources."""
        # Create a real file
        real_file = tmp_path / "real.css"
        real_file.write_text("/* real */")

        # Create a symlink to it
        symlink = tmp_path / "link.css"
        try:
            symlink.symlink_to(real_file)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        # Changed sources contains symlink
        changed_sources = {symlink}

        # should_bypass with real file should still match
        result = tracker.should_bypass(real_file, changed_sources)

        assert result is True

    def test_no_match_different_files(self, tracker: MockFileTracking, tmp_path: Path) -> None:
        """Test that different files don't match."""
        file1 = tmp_path / "file1.css"
        file1.write_text("/* file1 */")

        file2 = tmp_path / "file2.css"
        file2.write_text("/* file2 */")

        # Pre-cache file2 so is_changed returns False
        tracker.file_fingerprints[str(file2)] = {
            "mtime": file2.stat().st_mtime,
            "size": file2.stat().st_size,
            "hash": "dummy",
        }

        changed_sources = {file1}

        result = tracker.should_bypass(file2, changed_sources)

        assert result is False

    def test_empty_changed_sources_uses_hash(
        self, tracker: MockFileTracking, temp_file: Path
    ) -> None:
        """Test that empty changed_sources falls back to hash check."""
        # File not in cache, so is_changed should return True
        result = tracker.should_bypass(temp_file, None)

        assert result is True  # Not in cache = changed

    def test_path_with_parent_reference(self, tracker: MockFileTracking, tmp_path: Path) -> None:
        """Test paths with .. components are resolved correctly."""
        # Create subdirectory and file
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        test_file = subdir / "test.css"
        test_file.write_text("/* test */")

        # Create path with .. component
        path_with_parent = tmp_path / "subdir" / ".." / "subdir" / "test.css"

        changed_sources = {test_file}

        result = tracker.should_bypass(path_with_parent, changed_sources)

        assert result is True


class TestIsInTemplateDirPathResolution:
    """Tests for _is_in_template_dir path resolution in build_trigger."""

    def test_resolved_template_path(self, tmp_path: Path) -> None:
        """Test that template paths are resolved correctly."""
        from unittest.mock import MagicMock

        from bengal.server.build_trigger import BuildTrigger

        # Create template directory
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        template_file = templates_dir / "base.html"
        template_file.write_text("<html></html>")

        # Create path with ./ component
        path_with_dot = templates_dir / "." / "base.html"

        # Create mock site
        mock_site = MagicMock()
        mock_site.root_path = tmp_path
        mock_site.output_dir = tmp_path / "public"
        mock_site.config = {}
        mock_site.theme = None

        mock_executor = MagicMock()

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        result = trigger._is_in_template_dir(path_with_dot, [templates_dir])

        assert result is True

    def test_symlink_template_dir(self, tmp_path: Path) -> None:
        """Test that symlinked template directories work."""
        from unittest.mock import MagicMock

        from bengal.server.build_trigger import BuildTrigger

        # Create real template directory
        real_templates = tmp_path / "real_templates"
        real_templates.mkdir()

        template_file = real_templates / "base.html"
        template_file.write_text("<html></html>")

        # Create symlink to templates
        link_templates = tmp_path / "templates"
        try:
            link_templates.symlink_to(real_templates)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        # Create mock site
        mock_site = MagicMock()
        mock_site.root_path = tmp_path
        mock_site.output_dir = tmp_path / "public"
        mock_site.config = {}
        mock_site.theme = None

        mock_executor = MagicMock()

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Check file in real dir against symlink dir
        result = trigger._is_in_template_dir(template_file, [link_templates])

        assert result is True
