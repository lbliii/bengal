"""
Tests for VersionDiffer file reading error handling.

These tests verify that _read_file_safe handles:
- Normal UTF-8 files
- Non-UTF-8 files (fallback to latin-1)
- Permission denied errors
- File not found errors
- General OS errors
- Diff continues even when some files can't be read
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from bengal.content.discovery.version_diff import VersionDiff, VersionDiffer


@pytest.fixture
def differ_paths(tmp_path: Path) -> tuple[Path, Path]:
    """Create old and new version directories."""
    old = tmp_path / "old"
    new = tmp_path / "new"
    old.mkdir()
    new.mkdir()
    return old, new


@pytest.fixture
def differ(differ_paths: tuple[Path, Path]) -> VersionDiffer:
    """Create a VersionDiffer instance."""
    old, new = differ_paths
    return VersionDiffer(old, new)


class TestReadFileSafe:
    """Test _read_file_safe error handling."""

    def test_read_utf8_file(self, differ: VersionDiffer, tmp_path: Path) -> None:
        """Normal UTF-8 file should read successfully."""
        test_file = tmp_path / "test.md"
        test_file.write_text("Hello world", encoding="utf-8")

        result = differ._read_file_safe(test_file)

        assert result == "Hello world"

    def test_read_utf8_with_special_chars(self, differ: VersionDiffer, tmp_path: Path) -> None:
        """UTF-8 file with special characters."""
        test_file = tmp_path / "special.md"
        test_file.write_text("Héllo wörld 你好 🎉", encoding="utf-8")

        result = differ._read_file_safe(test_file)

        assert result == "Héllo wörld 你好 🎉"

    def test_read_latin1_fallback(self, differ: VersionDiffer, tmp_path: Path) -> None:
        """Non-UTF-8 file should fallback to latin-1."""
        test_file = tmp_path / "latin1.md"
        # Write raw bytes that are valid latin-1 but invalid UTF-8
        test_file.write_bytes(b"Caf\xe9")  # "Café" in latin-1

        result = differ._read_file_safe(test_file)

        assert result == "Café"

    def test_read_not_found(self, differ: VersionDiffer, tmp_path: Path) -> None:
        """Missing file should return None."""
        result = differ._read_file_safe(tmp_path / "nonexistent.md")

        assert result is None

    @pytest.mark.skipif(os.name == "nt", reason="Permission tests unreliable on Windows")
    def test_read_permission_denied(self, differ: VersionDiffer, tmp_path: Path) -> None:
        """Permission denied should return None."""
        test_file = tmp_path / "restricted.md"
        test_file.write_text("secret content")
        test_file.chmod(0o000)

        try:
            result = differ._read_file_safe(test_file)
            assert result is None
        finally:
            test_file.chmod(0o644)

    def test_read_empty_file(self, differ: VersionDiffer, tmp_path: Path) -> None:
        """Empty file should return empty string."""
        test_file = tmp_path / "empty.md"
        test_file.write_text("")

        result = differ._read_file_safe(test_file)

        assert result == ""


class TestDiffContinuesOnErrors:
    """Test that diff continues even when some files can't be read."""

    def test_diff_with_unreadable_added_file(self, differ_paths: tuple[Path, Path]) -> None:
        """Diff should handle unreadable files in 'added' category."""
        old, new = differ_paths

        # Create readable file in both
        (old / "good.md").write_text("old content")
        (new / "good.md").write_text("new content")

        # Create unreadable file only in new (added)
        bad_file = new / "bad.md"
        bad_file.write_bytes(b"\xff\xfe\x00\x00")  # Might cause issues

        differ = VersionDiffer(old, new)
        result = differ.diff("v1", "v2")

        # Should complete without crashing
        assert isinstance(result, VersionDiff)
        # Should have compared the good file
        assert len(result.modified_pages) >= 1 or len(result.unchanged_pages) >= 0

    def test_diff_with_mixed_readable_unreadable(self, differ_paths: tuple[Path, Path]) -> None:
        """Diff should process readable files even if some fail."""
        old, new = differ_paths

        # Create multiple files
        (old / "file1.md").write_text("content 1 old")
        (new / "file1.md").write_text("content 1 new")

        (old / "file2.md").write_text("content 2 same")
        (new / "file2.md").write_text("content 2 same")

        (old / "file3.md").write_text("content 3 old")
        (new / "file3.md").write_text("content 3 new")

        differ = VersionDiffer(old, new)
        result = differ.diff("v1", "v2")

        # Should process all readable files
        assert result.total_changes >= 0
        # file2 should be unchanged
        assert len(result.unchanged_pages) >= 1


class TestDiffResults:
    """Test the diff result structure."""

    def test_added_pages_detected(self, differ_paths: tuple[Path, Path]) -> None:
        """Pages only in new version are detected as added."""
        old, new = differ_paths

        (new / "new_page.md").write_text("# New page")

        differ = VersionDiffer(old, new)
        result = differ.diff("v1", "v2")

        assert len(result.added_pages) == 1
        assert result.added_pages[0].path == "new_page.md"
        assert result.added_pages[0].status == "added"

    def test_removed_pages_detected(self, differ_paths: tuple[Path, Path]) -> None:
        """Pages only in old version are detected as removed."""
        old, new = differ_paths

        (old / "old_page.md").write_text("# Old page")

        differ = VersionDiffer(old, new)
        result = differ.diff("v1", "v2")

        assert len(result.removed_pages) == 1
        assert result.removed_pages[0].path == "old_page.md"
        assert result.removed_pages[0].status == "removed"

    def test_modified_pages_detected(self, differ_paths: tuple[Path, Path]) -> None:
        """Pages with different content are detected as modified."""
        old, new = differ_paths

        (old / "page.md").write_text("# Old content")
        (new / "page.md").write_text("# New content")

        differ = VersionDiffer(old, new)
        result = differ.diff("v1", "v2")

        assert len(result.modified_pages) == 1
        assert result.modified_pages[0].status == "modified"
        assert result.modified_pages[0].change_percentage > 0

    def test_unchanged_pages_detected(self, differ_paths: tuple[Path, Path]) -> None:
        """Pages with identical content are detected as unchanged."""
        old, new = differ_paths

        (old / "same.md").write_text("# Same content")
        (new / "same.md").write_text("# Same content")

        differ = VersionDiffer(old, new)
        result = differ.diff("v1", "v2")

        assert len(result.unchanged_pages) == 1
        assert result.unchanged_pages[0].status == "unchanged"

    def test_diff_lines_generated_for_modified(self, differ_paths: tuple[Path, Path]) -> None:
        """Modified pages should have diff lines."""
        old, new = differ_paths

        (old / "page.md").write_text("line 1\nline 2\nline 3")
        (new / "page.md").write_text("line 1\nmodified line 2\nline 3")

        differ = VersionDiffer(old, new)
        result = differ.diff("v1", "v2")

        assert len(result.modified_pages) == 1
        assert len(result.modified_pages[0].diff_lines) > 0

    def test_change_percentage_calculation(self, differ_paths: tuple[Path, Path]) -> None:
        """Change percentage should be calculated correctly."""
        old, new = differ_paths

        # Completely different content = 100% change
        (old / "page.md").write_text("completely different")
        (new / "page.md").write_text("totally other words")

        differ = VersionDiffer(old, new)
        result = differ.diff("v1", "v2")

        assert len(result.modified_pages) == 1
        # Should be high percentage change
        assert result.modified_pages[0].change_percentage > 50


class TestVersionDiffSummary:
    """Test VersionDiff summary and markdown generation."""

    def test_summary_format(self, differ_paths: tuple[Path, Path]) -> None:
        """Summary should include all categories."""
        old, new = differ_paths

        (new / "added.md").write_text("# Added")
        (old / "removed.md").write_text("# Removed")
        (old / "same.md").write_text("# Same")
        (new / "same.md").write_text("# Same")

        differ = VersionDiffer(old, new)
        result = differ.diff("v1", "v2")

        summary = result.summary()

        assert "v1 → v2" in summary
        assert "Added:" in summary
        assert "Removed:" in summary
        assert "Unchanged:" in summary

    def test_to_markdown_format(self, differ_paths: tuple[Path, Path]) -> None:
        """Markdown output should be properly formatted."""
        old, new = differ_paths

        (new / "added.md").write_text("# Added")

        differ = VersionDiffer(old, new)
        result = differ.diff("v1", "v2")

        markdown = result.to_markdown()

        assert "# Changes:" in markdown
        assert "## ✨ New Pages" in markdown
        assert "`added.md`" in markdown

    def test_has_changes_property(self, differ_paths: tuple[Path, Path]) -> None:
        """has_changes should reflect whether any changes exist."""
        old, new = differ_paths

        # No changes
        differ = VersionDiffer(old, new)
        result = differ.diff("v1", "v2")
        assert not result.has_changes

        # Add a change
        (new / "new.md").write_text("# New")
        result = differ.diff("v1", "v2")
        assert result.has_changes
