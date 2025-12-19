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

    def test_watchdog_filter_returns_true_for_ignored(self) -> None:
        """Test that watchdog filter returns True for ignored paths."""
        f = IgnoreFilter(glob_patterns=["*.pyc"], include_defaults=False)
        filter_fn = f.as_watchdog_filter()

        # Returns True to IGNORE
        assert filter_fn(Path("/project/app.pyc")) is True
        assert filter_fn(Path("/project/app.py")) is False


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
