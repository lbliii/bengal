"""
Tests for bengal.cache.utils functions.

Tests clear_build_cache, clear_output_directory, and clear_template_cache utilities.
"""

from __future__ import annotations

from pathlib import Path

from bengal.cache import clear_build_cache, clear_output_directory, clear_template_cache
from bengal.cache.paths import BengalPaths


class TestClearBuildCache:
    """Tests for clear_build_cache function."""

    def test_clears_existing_cache(self, tmp_path: Path) -> None:
        """Test that existing build cache is cleared."""
        paths = BengalPaths(tmp_path)
        paths.ensure_dirs()

        # Create a cache file
        cache_file = paths.build_cache
        cache_file.write_text('{"test": true}')
        assert cache_file.exists()

        # Clear cache
        result = clear_build_cache(tmp_path)

        assert result is True
        assert not cache_file.exists()

    def test_returns_false_when_no_cache(self, tmp_path: Path) -> None:
        """Test that function returns False when no cache exists."""
        result = clear_build_cache(tmp_path)
        assert result is False

    def test_handles_path_as_string(self, tmp_path: Path) -> None:
        """Test that function works with string path."""
        paths = BengalPaths(tmp_path)
        paths.ensure_dirs()
        paths.build_cache.write_text('{"test": true}')

        result = clear_build_cache(str(tmp_path))  # String instead of Path
        assert result is True


class TestClearOutputDirectory:
    """Tests for clear_output_directory function."""

    def test_clears_existing_output_directory(self, tmp_path: Path) -> None:
        """Test that existing output directory is cleared."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html></html>")
        (output_dir / "subdir").mkdir()
        (output_dir / "subdir" / "page.html").write_text("<html></html>")

        result = clear_output_directory(output_dir)

        assert result is True
        assert not output_dir.exists()

    def test_returns_false_when_no_directory(self, tmp_path: Path) -> None:
        """Test that function returns False when directory doesn't exist."""
        output_dir = tmp_path / "nonexistent"
        result = clear_output_directory(output_dir)
        assert result is False


class TestClearTemplateCache:
    """Tests for clear_template_cache function."""

    def test_clears_existing_template_cache(self, tmp_path: Path) -> None:
        """Test that existing template cache directory is cleared."""
        paths = BengalPaths(tmp_path)
        paths.ensure_dirs()

        # Create template cache files
        templates_dir = paths.templates_dir
        templates_dir.mkdir(parents=True, exist_ok=True)
        (templates_dir / "__bengal_template_abc123.cache").write_bytes(b"\x00\x01\x02")
        (templates_dir / "__bengal_template_def456.cache").write_bytes(b"\x00\x01\x02")
        assert templates_dir.exists()
        assert len(list(templates_dir.glob("*.cache"))) == 2

        # Clear template cache
        result = clear_template_cache(tmp_path)

        assert result is True
        assert not templates_dir.exists()

    def test_returns_false_when_no_cache(self, tmp_path: Path) -> None:
        """Test that function returns False when no template cache exists."""
        result = clear_template_cache(tmp_path)
        assert result is False

    def test_handles_path_as_string(self, tmp_path: Path) -> None:
        """Test that function works with string path."""
        paths = BengalPaths(tmp_path)
        paths.ensure_dirs()
        templates_dir = paths.templates_dir
        templates_dir.mkdir(parents=True, exist_ok=True)
        (templates_dir / "test.cache").write_bytes(b"\x00")

        result = clear_template_cache(str(tmp_path))  # String instead of Path
        assert result is True
        assert not templates_dir.exists()
