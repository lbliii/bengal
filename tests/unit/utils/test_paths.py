"""Tests for path utilities.

Note: These tests use LegacyBengalPaths for the static method interface.
For new code, prefer the instance-based bengal.cache.paths.BengalPaths.
"""

from pathlib import Path

from bengal.utils.paths import LegacyBengalPaths as BengalPaths


class TestGetProfileDir:
    """Test get_profile_dir() method."""

    def test_creates_profile_directory(self, tmp_path):
        """Test that profile directory is created."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        profile_dir = BengalPaths.get_profile_dir(source_dir)

        assert profile_dir.exists()
        assert profile_dir.is_dir()
        assert profile_dir == source_dir / ".bengal" / "profiles"

    def test_idempotent_creation(self, tmp_path):
        """Test that calling multiple times is safe."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        dir1 = BengalPaths.get_profile_dir(source_dir)
        dir2 = BengalPaths.get_profile_dir(source_dir)

        assert dir1 == dir2
        assert dir1.exists()

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created if missing."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # .bengal doesn't exist yet
        assert not (source_dir / ".bengal").exists()

        profile_dir = BengalPaths.get_profile_dir(source_dir)

        assert (source_dir / ".bengal").exists()
        assert profile_dir.exists()


class TestGetLogDir:
    """Test get_log_dir() method."""

    def test_creates_log_directory(self, tmp_path):
        """Test that log directory is created."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        log_dir = BengalPaths.get_log_dir(source_dir)

        assert log_dir.exists()
        assert log_dir.is_dir()
        assert log_dir == source_dir / ".bengal" / "logs"

    def test_idempotent_creation(self, tmp_path):
        """Test that calling multiple times is safe."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        dir1 = BengalPaths.get_log_dir(source_dir)
        dir2 = BengalPaths.get_log_dir(source_dir)

        assert dir1 == dir2
        assert dir1.exists()


class TestGetBuildLogPath:
    """Test get_build_log_path() method."""

    def test_default_log_path(self, tmp_path):
        """Test default build log path."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        log_path = BengalPaths.get_build_log_path(source_dir)

        assert log_path == source_dir / ".bengal" / "logs" / "build.log"

    def test_custom_log_path(self, tmp_path):
        """Test custom build log path."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        custom_path = tmp_path / "custom" / "build.log"

        log_path = BengalPaths.get_build_log_path(source_dir, custom_path)

        assert log_path == custom_path

    def test_custom_path_overrides_default(self, tmp_path):
        """Test that custom path takes precedence."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        custom_path = tmp_path / "elsewhere" / "log.txt"

        log_path = BengalPaths.get_build_log_path(source_dir, custom_path)

        assert log_path == custom_path
        assert log_path != source_dir / ".bengal" / "logs" / "build.log"


class TestGetProfilePath:
    """Test get_profile_path() method."""

    def test_default_profile_path(self, tmp_path):
        """Test default profile path."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        profile_path = BengalPaths.get_profile_path(source_dir)

        assert profile_path == source_dir / ".bengal" / "profiles" / "build_profile.stats"
        assert profile_path.parent.exists()

    def test_custom_profile_path(self, tmp_path):
        """Test custom profile path."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        custom_path = tmp_path / "custom" / "profile.stats"

        profile_path = BengalPaths.get_profile_path(source_dir, custom_path)

        assert profile_path == custom_path

    def test_custom_filename(self, tmp_path):
        """Test custom filename for profile."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        profile_path = BengalPaths.get_profile_path(source_dir, filename="custom.stats")

        assert profile_path == source_dir / ".bengal" / "profiles" / "custom.stats"
        assert profile_path.parent.exists()

    def test_custom_path_ignores_filename(self, tmp_path):
        """Test that custom path ignores filename parameter."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        custom_path = tmp_path / "explicit.stats"

        profile_path = BengalPaths.get_profile_path(
            source_dir, custom_path=custom_path, filename="ignored.stats"
        )

        assert profile_path == custom_path


class TestGetCachePath:
    """Test get_cache_path() method."""

    def test_cache_path_in_output_dir(self, tmp_path):
        """Test cache path is in output directory."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        cache_path = BengalPaths.get_cache_path(output_dir)

        assert cache_path == output_dir / ".bengal-cache.json"

    def test_cache_path_no_creation(self, tmp_path):
        """Test that cache path doesn't create directories."""
        output_dir = tmp_path / "public"
        # Don't create output_dir

        cache_path = BengalPaths.get_cache_path(output_dir)

        # Should return path even if directory doesn't exist
        assert cache_path == output_dir / ".bengal-cache.json"
        # But directory should not be created
        assert not output_dir.exists()


class TestGetTemplateCacheDir:
    """Test get_template_cache_dir() method."""

    def test_creates_template_cache_directory(self, tmp_path):
        """Test that template cache directory is created."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        cache_dir = BengalPaths.get_template_cache_dir(output_dir)

        assert cache_dir.exists()
        assert cache_dir.is_dir()
        assert cache_dir == output_dir / ".bengal-cache" / "templates"

    def test_creates_parent_cache_directory(self, tmp_path):
        """Test that parent .bengal-cache directory is created."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        cache_dir = BengalPaths.get_template_cache_dir(output_dir)

        assert (output_dir / ".bengal-cache").exists()
        assert cache_dir.exists()

    def test_idempotent_creation(self, tmp_path):
        """Test that calling multiple times is safe."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        dir1 = BengalPaths.get_template_cache_dir(output_dir)
        dir2 = BengalPaths.get_template_cache_dir(output_dir)

        assert dir1 == dir2
        assert dir1.exists()


class TestDirectoryStructure:
    """Test overall directory structure consistency."""

    def test_source_vs_output_separation(self, tmp_path):
        """Test that source and output directories have separate paths."""
        source_dir = tmp_path / "source"
        output_dir = tmp_path / "public"
        source_dir.mkdir()
        output_dir.mkdir()

        # Source-related paths
        profile_dir = BengalPaths.get_profile_dir(source_dir)
        log_dir = BengalPaths.get_log_dir(source_dir)
        build_log = BengalPaths.get_build_log_path(source_dir)

        # Output-related paths
        cache_file = BengalPaths.get_cache_path(output_dir)
        template_cache = BengalPaths.get_template_cache_dir(output_dir)

        # Source paths should be under source_dir
        assert profile_dir.is_relative_to(source_dir)
        assert log_dir.is_relative_to(source_dir)
        assert build_log.is_relative_to(source_dir)

        # Output paths should be under output_dir
        assert cache_file.is_relative_to(output_dir)
        assert template_cache.is_relative_to(output_dir)

    def test_all_bengal_paths_use_dot_prefix(self, tmp_path):
        """Test that all Bengal paths use dot prefix for hidden files/dirs."""
        source_dir = tmp_path / "source"
        output_dir = tmp_path / "public"
        source_dir.mkdir()
        output_dir.mkdir()

        profile_dir = BengalPaths.get_profile_dir(source_dir)
        log_dir = BengalPaths.get_log_dir(source_dir)
        build_log = BengalPaths.get_build_log_path(source_dir)
        cache_file = BengalPaths.get_cache_path(output_dir)
        template_cache = BengalPaths.get_template_cache_dir(output_dir)

        # All should use .bengal prefix
        assert ".bengal" in str(profile_dir)
        assert ".bengal" in str(log_dir)
        assert ".bengal" in str(build_log)
        assert ".bengal" in str(cache_file)
        assert ".bengal" in str(template_cache)


class TestStaticMethodBehavior:
    """Test that all methods work as static methods."""

    def test_can_call_without_instance(self, tmp_path):
        """Test that methods can be called without creating instance."""
        source_dir = tmp_path / "source"
        output_dir = tmp_path / "public"
        source_dir.mkdir()
        output_dir.mkdir()

        # All these should work without creating BengalPaths instance
        profile_dir = BengalPaths.get_profile_dir(source_dir)
        log_dir = BengalPaths.get_log_dir(source_dir)
        build_log = BengalPaths.get_build_log_path(source_dir)
        profile_path = BengalPaths.get_profile_path(source_dir)
        cache_path = BengalPaths.get_cache_path(output_dir)
        template_cache = BengalPaths.get_template_cache_dir(output_dir)

        # All should return valid paths
        assert isinstance(profile_dir, Path)
        assert isinstance(log_dir, Path)
        assert isinstance(build_log, Path)
        assert isinstance(profile_path, Path)
        assert isinstance(cache_path, Path)
        assert isinstance(template_cache, Path)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_nested_source_directory(self, tmp_path):
        """Test with deeply nested source directory."""
        source_dir = tmp_path / "very" / "deep" / "nested" / "source"
        source_dir.mkdir(parents=True)

        profile_dir = BengalPaths.get_profile_dir(source_dir)

        assert profile_dir.exists()
        assert profile_dir == source_dir / ".bengal" / "profiles"

    def test_relative_paths(self, tmp_path):
        """Test with relative paths."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            source_dir = Path("source")
            source_dir.mkdir()

            profile_dir = BengalPaths.get_profile_dir(source_dir)

            assert profile_dir.exists()
            # Should work with relative paths
            assert ".bengal" in str(profile_dir)
            assert "profiles" in str(profile_dir)

        finally:
            os.chdir(original_cwd)

    def test_absolute_paths(self, tmp_path):
        """Test with absolute paths."""
        source_dir = tmp_path.resolve() / "source"
        source_dir.mkdir()

        profile_dir = BengalPaths.get_profile_dir(source_dir)

        assert profile_dir.is_absolute()
        assert profile_dir.exists()

    def test_paths_with_spaces(self, tmp_path):
        """Test with paths containing spaces."""
        source_dir = tmp_path / "my source directory"
        source_dir.mkdir()

        profile_dir = BengalPaths.get_profile_dir(source_dir)

        assert profile_dir.exists()
        assert "my source directory" in str(profile_dir)

    def test_paths_with_unicode(self, tmp_path):
        """Test with paths containing unicode characters."""
        source_dir = tmp_path / "source_测试_مصدر"
        source_dir.mkdir()

        profile_dir = BengalPaths.get_profile_dir(source_dir)

        assert profile_dir.exists()
