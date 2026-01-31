"""
Unit tests for IgnoreFilter class.

Tests:
- Glob pattern matching
- Regex pattern matching
- Directory ignores
- Default ignored directories
- from_config factory method
- Filter callbacks for watchfiles/watchdog

"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.server.ignore_filter import IgnoreFilter


class TestIgnoreFilterGlobPatterns:
    """Tests for glob pattern matching."""

    def test_glob_matches_file_extension(self) -> None:
        """Test that glob patterns match file extensions."""
        f = IgnoreFilter(glob_patterns=["*.pyc"], include_defaults=False)

        assert f(Path("/project/foo.pyc")) is True
        assert f(Path("/project/bar.pyc")) is True
        assert f(Path("/project/foo.py")) is False

    def test_glob_matches_filename(self) -> None:
        """Test that glob patterns match exact filenames."""
        f = IgnoreFilter(glob_patterns=[".DS_Store"], include_defaults=False)

        assert f(Path("/project/.DS_Store")) is True
        assert f(Path("/project/subdir/.DS_Store")) is True
        assert f(Path("/project/file.txt")) is False

    def test_glob_matches_multiple_patterns(self) -> None:
        """Test that multiple glob patterns work."""
        f = IgnoreFilter(
            glob_patterns=["*.pyc", "*.pyo", "*.tmp"],
            include_defaults=False,
        )

        assert f(Path("/project/foo.pyc")) is True
        assert f(Path("/project/bar.pyo")) is True
        assert f(Path("/project/baz.tmp")) is True
        assert f(Path("/project/file.py")) is False


class TestIgnoreFilterRegexPatterns:
    """Tests for regex pattern matching."""

    def test_regex_matches_minified_files(self) -> None:
        """Test that regex patterns match minified files."""
        f = IgnoreFilter(
            regex_patterns=[r".*\.min\.(js|css)$"],
            include_defaults=False,
        )

        assert f(Path("/project/app.min.js")) is True
        assert f(Path("/project/styles.min.css")) is True
        assert f(Path("/project/app.js")) is False
        assert f(Path("/project/styles.css")) is False

    def test_regex_matches_node_modules(self) -> None:
        """Test that regex patterns match node_modules anywhere."""
        f = IgnoreFilter(
            regex_patterns=[r"/node_modules/"],
            include_defaults=False,
        )

        assert f(Path("/project/node_modules/package/file.js")) is True
        assert f(Path("/project/app/node_modules/lodash/index.js")) is True
        assert f(Path("/project/src/app.js")) is False

    def test_regex_matches_hidden_directories(self) -> None:
        """Test that regex patterns match hidden directories."""
        f = IgnoreFilter(
            regex_patterns=[r"/\.[^/]+/"],
            include_defaults=False,
        )

        assert f(Path("/project/.cache/file.txt")) is True
        assert f(Path("/project/.hidden/data.json")) is True
        assert f(Path("/project/visible/file.txt")) is False


class TestIgnoreFilterDirectories:
    """Tests for directory ignores."""

    def test_ignores_files_in_specified_directory(self, tmp_path: Path) -> None:
        """Test that files in specified directories are ignored."""
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()

        f = IgnoreFilter(directories=[dist_dir], include_defaults=False)

        assert f(dist_dir / "app.js") is True
        assert f(dist_dir / "assets" / "style.css") is True
        assert f(tmp_path / "src" / "app.js") is False

    def test_ignores_multiple_directories(self, tmp_path: Path) -> None:
        """Test that multiple directories can be ignored."""
        dist_dir = tmp_path / "dist"
        build_dir = tmp_path / "build"
        dist_dir.mkdir()
        build_dir.mkdir()

        f = IgnoreFilter(directories=[dist_dir, build_dir], include_defaults=False)

        assert f(dist_dir / "file.js") is True
        assert f(build_dir / "file.js") is True
        assert f(tmp_path / "src" / "file.js") is False


class TestIgnoreFilterDefaults:
    """Tests for default ignored directories."""

    @pytest.mark.parametrize(
        "dirname",
        [
            ".git",
            ".hg",
            ".svn",
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            "node_modules",
            ".nox",
            ".tox",
            ".idea",
            ".vscode",
            ".bengal",
        ],
    )
    def test_default_directories_are_ignored(self, dirname: str) -> None:
        """Test that default directories are ignored when include_defaults=True."""
        f = IgnoreFilter(include_defaults=True)

        assert f(Path(f"/project/{dirname}/file.txt")) is True

    def test_default_directories_not_ignored_when_disabled(self) -> None:
        """Test that default directories are not ignored when include_defaults=False."""
        f = IgnoreFilter(include_defaults=False)

        # These should not be ignored when defaults are disabled
        assert f(Path("/project/.git/config")) is False
        assert f(Path("/project/node_modules/package.json")) is False


class TestIgnoreFilterFromConfig:
    """Tests for from_config factory method."""

    def test_creates_from_empty_config(self) -> None:
        """Test that from_config works with empty config."""
        config: dict = {}
        f = IgnoreFilter.from_config(config)

        # Should still apply defaults
        assert f(Path("/project/.git/config")) is True

    def test_creates_from_dev_server_config(self) -> None:
        """Test that from_config reads dev_server patterns."""
        config = {
            "dev_server": {
                "exclude_patterns": ["*.pyc", "__pycache__"],
                "exclude_regex": [r".*\.min\.js$"],
            }
        }
        f = IgnoreFilter.from_config(config)

        assert f(Path("/project/foo.pyc")) is True
        assert f(Path("/project/app.min.js")) is True

    def test_includes_output_dir(self, tmp_path: Path) -> None:
        """Test that output_dir is added to ignored directories."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        config: dict = {}
        f = IgnoreFilter.from_config(config, output_dir=output_dir)

        assert f(output_dir / "index.html") is True
        assert f(tmp_path / "content" / "post.md") is False

    def test_handles_dev_server_as_bool_gracefully(self) -> None:
        """Test that from_config handles dev_server being a bool (not a dict).

        This is defensive coding - the proper design uses site.dev_mode for
        runtime state, keeping config["dev_server"] as a dict for user settings.
        But we still handle the edge case gracefully.
        """
        # Edge case: dev_server is a bool instead of a dict
        config = {"dev_server": True}

        # Should NOT crash - should use defaults
        f = IgnoreFilter.from_config(config)

        # Should still work with default patterns
        assert f(Path("/project/.git/config")) is True

    def test_dev_server_config_is_dict_not_runtime_flag(self) -> None:
        """Test that config["dev_server"] is a dict for user settings.

        Runtime state (dev mode active) should be on site.dev_mode,
        not in config. This keeps config pure (static settings only).
        """
        config = {
            "dev_server": {  # User config (dict) - static settings
                "exclude_patterns": ["*.log"],
            },
        }
        # Note: site.dev_mode = True would be set separately for runtime state

        f = IgnoreFilter.from_config(config)

        # Should read user patterns correctly
        assert f(Path("/project/debug.log")) is True
        assert f(Path("/project/app.py")) is False


class TestIgnoreFilterCallbacks:
    """Tests for filter callback methods."""

    def test_watchfiles_filter_returns_true_for_included(self) -> None:
        """Test that watchfiles filter returns True for included paths."""
        f = IgnoreFilter(glob_patterns=["*.pyc"], include_defaults=False)
        filter_fn = f.as_watchfiles_filter()

        # Returns True to INCLUDE (opposite of ignore)
        assert filter_fn("modify", "/project/app.py") is True
        assert filter_fn("modify", "/project/app.pyc") is False


class TestIgnoreFilterEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_regex_raises_error(self) -> None:
        """Test that invalid regex patterns raise re.error."""
        import re

        with pytest.raises(re.error):
            IgnoreFilter(regex_patterns=["[invalid"])

    def test_empty_patterns_allow_all(self) -> None:
        """Test that empty patterns allow all files."""
        f = IgnoreFilter(include_defaults=False)

        assert f(Path("/project/any/file.txt")) is False
        assert f(Path("/project/deep/nested/path.md")) is False

    def test_resolves_relative_paths(self) -> None:
        """Test that relative paths are resolved correctly."""
        f = IgnoreFilter(glob_patterns=["*.pyc"], include_defaults=False)

        # Relative paths should be resolved
        assert f(Path("./foo.pyc")) is True
        assert f(Path("./foo.py")) is False


class TestIgnoreFilterBengalCache:
    """Tests for .bengal cache directory ignoring.

    The .bengal directory contains cache files that are written during builds.
    These must be ignored to prevent infinite rebuild loops in the dev server.

    """

    def test_bengal_cache_dir_is_ignored_by_default(self) -> None:
        """Test that .bengal cache directory is in default ignores."""
        f = IgnoreFilter(include_defaults=True)

        # Files inside .bengal should be ignored (both compressed and uncompressed formats)
        assert f(Path("/project/.bengal/cache.json")) is True
        assert f(Path("/project/.bengal/page_metadata.json")) is True
        assert f(Path("/project/.bengal/page_metadata.json.zst")) is True
        assert f(Path("/project/.bengal/taxonomy_index.json")) is True
        assert f(Path("/project/.bengal/taxonomy_index.json.zst")) is True
        assert f(Path("/project/.bengal/asset_deps.json")) is True
        assert f(Path("/project/.bengal/asset_deps.json.zst")) is True

    def test_bengal_cache_files_ignored_in_nested_paths(self) -> None:
        """Test that .bengal is ignored regardless of project location."""
        f = IgnoreFilter(include_defaults=True)

        # Deeply nested project paths
        assert f(Path("/home/user/sites/my-site/.bengal/cache.json.zst")) is True
        assert f(Path("/Users/dev/projects/docs/.bengal/asset_deps.json")) is True

    def test_bengal_cache_not_ignored_when_defaults_disabled(self) -> None:
        """Test that .bengal is NOT ignored when include_defaults=False."""
        f = IgnoreFilter(include_defaults=False)

        # Should not be ignored without defaults
        assert f(Path("/project/.bengal/cache.json")) is False

    def test_bengal_temp_files_ignored(self) -> None:
        """Test that temp files in .bengal directory are ignored.

        During cache writes, temporary files like .foo.json.12345.tmp are created.
        These must also be ignored.
        """
        f = IgnoreFilter(include_defaults=True)

        # Temp file patterns that appear during cache updates
        assert f(Path("/project/.bengal/.cache.json.12345.tmp")) is True
        assert f(Path("/project/.bengal/.author_index.json.89978.tmp")) is True


class TestIgnoreFilterCaching:
    """Tests for path result caching.

    RFC: rfc-server-package-optimizations
    The IgnoreFilter caches path check results for O(1) repeated lookups.

    """

    def test_cache_hit_returns_same_result(self) -> None:
        """Test that cache hit returns the same result."""
        f = IgnoreFilter(glob_patterns=["*.pyc"], include_defaults=False)

        path = Path("/project/foo.pyc")

        # First call - cache miss
        result1 = f(path)
        assert result1 is True

        # Second call - cache hit (should return same result)
        result2 = f(path)
        assert result2 is True
        assert result1 == result2

    def test_cache_different_paths(self) -> None:
        """Test that different paths are cached separately."""
        f = IgnoreFilter(glob_patterns=["*.pyc"], include_defaults=False)

        path1 = Path("/project/foo.pyc")
        path2 = Path("/project/bar.py")

        assert f(path1) is True
        assert f(path2) is False

        # Both should be cached
        assert str(path1) in f._path_cache
        assert str(path2) in f._path_cache

    def test_cache_eviction_when_full(self) -> None:
        """Test that LRU eviction works when cache is full."""
        # Small cache for testing
        f = IgnoreFilter(glob_patterns=["*.pyc"], include_defaults=False, cache_max_size=3)

        # Fill the cache
        paths = [Path(f"/project/file{i}.py") for i in range(5)]
        for path in paths:
            f(path)

        # Cache should be at max size
        assert len(f._path_cache) <= 3

    def test_clear_cache(self) -> None:
        """Test that clear_cache empties the cache."""
        f = IgnoreFilter(glob_patterns=["*.pyc"], include_defaults=False)

        # Populate cache
        f(Path("/project/foo.pyc"))
        f(Path("/project/bar.py"))
        assert len(f._path_cache) == 2

        # Clear cache
        f.clear_cache()
        assert len(f._path_cache) == 0

    def test_precompiled_glob_patterns(self) -> None:
        """Test that glob patterns are pre-compiled to regex."""
        f = IgnoreFilter(glob_patterns=["*.pyc", "*.pyo"], include_defaults=False)

        # Should have compiled patterns
        assert len(f._compiled_globs) == 2

        # Should still match correctly
        assert f(Path("/project/foo.pyc")) is True
        assert f(Path("/project/bar.pyo")) is True
        assert f(Path("/project/baz.py")) is False

    def test_cache_custom_max_size(self) -> None:
        """Test that cache_max_size is configurable."""
        f = IgnoreFilter(glob_patterns=["*.pyc"], include_defaults=False, cache_max_size=50)

        assert f._cache_max_size == 50
