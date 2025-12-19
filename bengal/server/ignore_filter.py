r"""
Flexible ignore filtering with glob and regex patterns.

Provides configurable filtering for file watching with support for:
- Glob patterns (e.g., "*.pyc", "**/__pycache__")
- Regex patterns (e.g., r".*\.min\.(js|css)$")
- Directory ignores (always ignore certain paths)
- Default ignores (common temp/cache directories)

Related:
    - bengal/server/watcher_runner.py: Uses IgnoreFilter for file watching
    - bengal/server/file_watcher.py: Integrates with file watcher backends
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class IgnoreFilter:
    r"""
    Filter for determining which paths to ignore during file watching.

    Supports glob patterns, regex patterns, and directory ignores.
    Default ignores are always applied (common temp/cache directories).

    Features:
        - Glob patterns: Standard shell wildcards (e.g., "*.pyc", "**/__pycache__")
        - Regex patterns: Full regex support (e.g., r".*\.min\.(js|css)$")
        - Directory ignores: Always ignore files under specific directories
        - Default ignores: Common development directories (.git, node_modules, etc.)

    Example:
        >>> filter = IgnoreFilter(
        ...     glob_patterns=["*.pyc", "__pycache__"],
        ...     regex_patterns=[r".*\.min\.(js|css)$"],
        ...     directories=[Path("/project/dist")],
        ... )
        >>> filter(Path("/project/foo.pyc"))
        True
        >>> filter(Path("/project/src/app.py"))
        False
    """

    # Default directories to always ignore (common development patterns)
    DEFAULT_IGNORED_DIRS: frozenset[str] = frozenset(
        {
            # Version control
            ".git",
            ".hg",
            ".svn",
            # Python virtual environments
            ".venv",
            "venv",
            ".env",
            # Python cache
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            # Node.js
            "node_modules",
            # Build tools
            ".nox",
            ".tox",
            "dist",
            "build",
            # IDE/Editor directories
            ".idea",
            ".vscode",
            # Coverage
            "coverage",
            "htmlcov",
            ".coverage",
            # Bengal cache directory
            ".bengal",
        }
    )

    def __init__(
        self,
        glob_patterns: list[str] | None = None,
        regex_patterns: list[str] | None = None,
        directories: list[Path] | None = None,
        *,
        include_defaults: bool = True,
    ) -> None:
        r"""
        Initialize ignore filter.

        Args:
            glob_patterns: Glob patterns (e.g., "*.pyc", "**/__pycache__")
            regex_patterns: Regex patterns (e.g., r".*\.min\.(js|css)$")
            directories: Directories to always ignore (resolved to absolute paths)
            include_defaults: Whether to include default ignored directories

        Raises:
            re.error: If a regex pattern is invalid
        """
        self.glob_patterns = list(glob_patterns) if glob_patterns else []
        self.regex_patterns = [re.compile(p) for p in (regex_patterns or [])]
        self.directories = [p.resolve() for p in (directories or [])]
        self.include_defaults = include_defaults

    def __call__(self, path: Path) -> bool:
        """
        Return True if path should be ignored.

        Args:
            path: Path to check (resolved to absolute)

        Returns:
            True if the path matches any ignore pattern, False otherwise
        """
        path = path.resolve()
        path_str = path.as_posix()

        # Check default directory names in path parts
        if self.include_defaults:
            for part in path.parts:
                if part in self.DEFAULT_IGNORED_DIRS:
                    return True

        # Check explicit directories
        for ignored_dir in self.directories:
            try:
                path.relative_to(ignored_dir)
                return True
            except ValueError:
                pass

        # Check glob patterns
        for pattern in self.glob_patterns:
            # Match against full path
            if fnmatch.fnmatch(path_str, pattern):
                return True
            # Also match against filename only
            if fnmatch.fnmatch(path.name, pattern):
                return True

        # Check regex patterns
        return any(regex.search(path_str) for regex in self.regex_patterns)

    @classmethod
    def from_config(
        cls,
        config: dict[str, Any],
        output_dir: Path | None = None,
    ) -> IgnoreFilter:
        r"""
        Create IgnoreFilter from bengal.toml config.

        Reads patterns from [dev_server] config section:
        - exclude_patterns: List of glob patterns
        - exclude_regex: List of regex patterns

        Args:
            config: Full site configuration dict
            output_dir: Output directory to always ignore (usually public/)

        Returns:
            Configured IgnoreFilter instance

        Example:
            >>> config = {
            ...     "dev_server": {
            ...         "exclude_patterns": ["*.pyc", "__pycache__"],
            ...         "exclude_regex": [r".*\\.min\\.(js|css)$"],
            ...     }
            ... }
            >>> filter = IgnoreFilter.from_config(config, Path("public/"))
        """
        dev_server = config.get("dev_server", {})

        # Note: dev_server should always be a dict (user settings).
        # Runtime state uses site.dev_mode, not config["dev_server"].
        if not isinstance(dev_server, dict):
            dev_server = {}

        directories: list[Path] = []
        if output_dir:
            directories.append(output_dir)

        return cls(
            glob_patterns=dev_server.get("exclude_patterns", []),
            regex_patterns=dev_server.get("exclude_regex", []),
            directories=directories,
        )

    def as_watchfiles_filter(self) -> Callable[[str, str], bool]:
        """
        Return a filter function compatible with watchfiles.

        watchfiles.awatch accepts a watch_filter callback with signature:
        (change_type: str, path: str) -> bool

        The filter should return True to INCLUDE the path (opposite of our __call__).

        Returns:
            Filter function for watchfiles.awatch
        """

        def filter_fn(change_type: str, path: str) -> bool:
            return not self(Path(path))

        return filter_fn
