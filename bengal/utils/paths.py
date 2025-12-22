"""
Path utilities for Bengal SSG.

Provides consistent path management for Bengal's internal directory structure,
including logs, profiles, metrics, and cache files. These utilities ensure
all Bengal state files are organized under a single `.bengal/` directory.

Key Features:
    - Centralized directory structure (`.bengal/`)
    - User-friendly path formatting for logs and errors
    - Separation of build outputs vs. Bengal state

Design Principles:
    All Bengal-generated state files (cache, logs, metrics, profiles) are
    stored under `.bengal/` in the source directory. This keeps the build
    output (`public/`) clean and deployable, while providing easy access
    to debugging information.

Directory Structure:
    .bengal/
    ├── cache.json.zst      # Build cache (compressed)
    ├── indexes/            # Query indexes
    ├── logs/
    │   ├── build.log       # Build logs
    │   └── serve.log       # Dev server logs
    ├── metrics/            # Performance metrics
    │   ├── history.jsonl   # Build history
    │   └── latest.json     # Latest build
    ├── profiles/           # cProfile output
    └── generated/          # Virtual pages

Related Modules:
    - bengal/cache/paths.py: Cache-specific paths
    - bengal/utils/path_resolver.py: CWD-independent path resolution
    - bengal/utils/url_normalization.py: URL path handling

See Also:
    - architecture/file-organization.md: Overall file organization
"""

from __future__ import annotations

from pathlib import Path


def format_path_for_display(
    path: Path | str | None,
    base_path: Path | None = None,
) -> str | None:
    """
    Format a path for user-friendly display in logs and warnings.

    Converts absolute paths to relative paths when possible, making error
    messages and logs more readable by avoiding user-specific directory prefixes.

    Args:
        path: Path to format. Accepts Path objects, strings, or None.
        base_path: Base directory to make paths relative to (typically
            site.root_path). If None, falls back to showing just the
            parent directory and filename.

    Returns:
        Formatted path string suitable for display, or None if path was None.

    Example:
        >>> site_root = Path("/home/user/mysite")
        >>> format_path_for_display(
        ...     Path("/home/user/mysite/content/blog/post.md"),
        ...     base_path=site_root
        ... )
        'content/blog/post.md'

        >>> # Without base_path, shows parent/filename
        >>> format_path_for_display(Path("/some/deep/path/file.md"))
        'path/file.md'

        >>> format_path_for_display(None)
        None

    Note:
        This function is used throughout Bengal for consistent path
        formatting in error messages, warnings, and log output.
    """
    if path is None:
        return None

    p = Path(path) if isinstance(path, str) else path

    # Try to make relative to base path
    if base_path is not None:
        try:
            return str(p.relative_to(base_path))
        except ValueError:
            pass  # Path not relative to base

    # Fallback: show just parent/filename for readability
    if p.is_absolute():
        return f"{p.parent.name}/{p.name}" if p.parent.name else p.name

    return str(p)


class BengalPaths:
    """
    Manages Bengal's internal directory structure for generated state files.

    This class provides static methods to access paths for Bengal's internal
    state files (logs, profiles, metrics, cache). All state is stored under
    `.bengal/` to keep the source directory clean and the output directory
    deployable.

    Directory Structure:
        .bengal/                    # All Bengal state (gitignored)
        ├── cache.json.zst          # Build cache (Zstandard compressed)
        ├── indexes/                # Query indexes for fast lookups
        ├── logs/
        │   ├── build.log           # Build logs (JSON lines)
        │   └── serve.log           # Dev server logs
        ├── metrics/
        │   ├── history.jsonl       # Build performance history
        │   └── latest.json         # Most recent build metrics
        ├── profiles/               # cProfile output for optimization
        └── generated/              # Virtual source paths for generated pages

    Design Rationale:
        Separating Bengal state from build outputs allows:
        1. Clean deployment (public/ contains only deployable files)
        2. Easy .gitignore management (just ignore .bengal/)
        3. Centralized debugging info (logs, metrics, profiles in one place)
        4. Safe cache clearing (delete .bengal/ to reset state)

    Example:
        >>> from bengal.utils.paths import BengalPaths
        >>> source_dir = Path("/home/user/mysite")
        >>>
        >>> # Get paths for various state files
        >>> log_path = BengalPaths.get_build_log_path(source_dir)
        >>> profile_path = BengalPaths.get_profile_path(source_dir)

    Related:
        - bengal/cache/paths.py: Lower-level path definitions
        - bengal/utils/path_resolver.py: CWD-independent resolution
    """

    @staticmethod
    def get_profile_dir(source_dir: Path) -> Path:
        """
        Get the directory for storing performance profiles.

        Creates the directory if it doesn't exist. Used for storing
        cProfile output when profiling builds.

        Args:
            source_dir: Site source directory (where bengal.toml lives).

        Returns:
            Path to `.bengal/profiles/` directory (created if needed).

        Example:
            >>> profile_dir = BengalPaths.get_profile_dir(Path("."))
            >>> profile_dir
            PosixPath('.bengal/profiles')
        """
        from bengal.cache.paths import BengalPaths as CachePaths

        paths = CachePaths(source_dir)
        paths.profiles_dir.mkdir(parents=True, exist_ok=True)
        return paths.profiles_dir

    @staticmethod
    def get_log_dir(source_dir: Path) -> Path:
        """
        Get the directory for storing build and server logs.

        Creates the directory if it doesn't exist. Logs are stored
        in JSON lines format for structured querying.

        Args:
            source_dir: Site source directory (where bengal.toml lives).

        Returns:
            Path to `.bengal/logs/` directory (created if needed).

        Example:
            >>> log_dir = BengalPaths.get_log_dir(Path("/mysite"))
            >>> log_dir
            PosixPath('/mysite/.bengal/logs')
        """
        from bengal.cache.paths import BengalPaths as CachePaths

        paths = CachePaths(source_dir)
        paths.logs_dir.mkdir(parents=True, exist_ok=True)
        return paths.logs_dir

    @staticmethod
    def get_build_log_path(source_dir: Path, custom_path: Path | None = None) -> Path:
        """
        Get the path for the build log file.

        Returns a custom path if provided (via CLI `--log` option),
        otherwise returns the default location.

        Args:
            source_dir: Site source directory.
            custom_path: Optional user-specified path from CLI.

        Returns:
            Path to build log file (default: `.bengal/logs/build.log`).

        Example:
            >>> # Default location
            >>> BengalPaths.get_build_log_path(Path("."))
            PosixPath('.bengal/logs/build.log')

            >>> # Custom location
            >>> BengalPaths.get_build_log_path(Path("."), Path("/tmp/build.log"))
            PosixPath('/tmp/build.log')
        """
        if custom_path:
            return custom_path

        log_dir = BengalPaths.get_log_dir(source_dir)
        return log_dir / "build.log"

    @staticmethod
    def get_serve_log_path(source_dir: Path, custom_path: Path | None = None) -> Path:
        """
        Get the path for the dev server log file.

        Args:
            source_dir: Site source directory.
            custom_path: Optional user-specified path from CLI.

        Returns:
            Path to serve log file (default: `.bengal/logs/serve.log`).

        Example:
            >>> BengalPaths.get_serve_log_path(Path("."))
            PosixPath('.bengal/logs/serve.log')
        """
        if custom_path:
            return custom_path

        log_dir = BengalPaths.get_log_dir(source_dir)
        return log_dir / "serve.log"

    @staticmethod
    def get_profile_path(
        source_dir: Path, custom_path: Path | None = None, filename: str = "build_profile.stats"
    ) -> Path:
        """
        Get the path for a performance profile file.

        Profile files are cProfile-compatible `.stats` files that can be
        analyzed with snakeviz, pstats, or other profiling tools.

        Args:
            source_dir: Site source directory.
            custom_path: Optional user-specified path from CLI.
            filename: Profile filename (default: 'build_profile.stats').

        Returns:
            Path to profile file.

        Example:
            >>> BengalPaths.get_profile_path(Path("."))
            PosixPath('.bengal/profiles/build_profile.stats')

            >>> # Custom filename for incremental builds
            >>> BengalPaths.get_profile_path(Path("."), filename="incremental.stats")
            PosixPath('.bengal/profiles/incremental.stats')
        """
        if custom_path:
            return custom_path

        profile_dir = BengalPaths.get_profile_dir(source_dir)
        return profile_dir / filename

    @staticmethod
    def get_cache_path(output_dir: Path) -> Path:
        """
        Get the path for the legacy build cache file.

        Note:
            This is a legacy path. New cache implementations use
            `.bengal/cache.json.zst` in the source directory instead.

        Args:
            output_dir: Output directory (public/).

        Returns:
            Path to `.bengal-cache.json` in output directory.
        """
        return output_dir / ".bengal-cache.json"

    @staticmethod
    def get_template_cache_dir(output_dir: Path) -> Path:
        """
        Get the directory for Jinja2 bytecode cache.

        Jinja2's bytecode cache speeds up template loading by caching
        compiled templates. Created if it doesn't exist.

        Args:
            output_dir: Output directory (public/).

        Returns:
            Path to `.bengal-cache/templates/` directory (created if needed).

        Note:
            Template cache is stored in output directory for backward
            compatibility. May move to `.bengal/` in future versions.
        """
        cache_dir = output_dir / ".bengal-cache" / "templates"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
