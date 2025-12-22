"""
Single source of truth for Bengal state directory paths.

This module defines all paths within the `.bengal` state directory, providing
a centralized location for cache files, indexes, logs, and runtime state.
Use BengalPaths instead of hardcoding `.bengal` strings throughout the codebase.

Constants:
    STATE_DIR_NAME: The state directory name (".bengal")

Classes:
    BengalPaths: Accessor for all state directory paths

Directory Structure:
    .bengal/
    ├── cache.json.zst       # Main build cache (compressed)
    ├── page_metadata.json   # Page discovery cache
    ├── asset_deps.json      # Asset dependency map
    ├── taxonomy_index.json  # Taxonomy index
    ├── build_history.json   # Build history for delta analysis
    ├── server.pid           # Dev server PID
    ├── asset-manifest.json  # Asset manifest
    ├── indexes/             # Query indexes (section, author, etc.)
    ├── templates/           # Jinja bytecode cache
    ├── content_cache/       # Remote content cache
    ├── logs/                # Build/serve logs
    ├── metrics/             # Performance metrics
    ├── profiles/            # Profiling output
    ├── themes/              # Theme state (swizzle registry)
    │   └── sources.json
    ├── js_bundle/           # JS bundle temporary files
    ├── pipeline_out/        # Asset pipeline temporary output
    └── generated/           # Generated content (auto-pages, etc.)

Usage:
    from bengal.cache.paths import BengalPaths, STATE_DIR_NAME

    # Create paths accessor
    paths = BengalPaths(site.root_path)

    # Access specific paths
    cache_path = paths.build_cache      # .bengal/cache.json
    logs_dir = paths.logs_dir           # .bengal/logs/

    # Create all directories
    paths.ensure_dirs()

    # Or access via Site
    cache_path = site.paths.build_cache

Related:
    - bengal.cache.build_cache: Uses paths.build_cache
    - bengal.rendering.template_engine: Uses paths.templates_dir
    - bengal.core.site: Site.paths property returns BengalPaths
"""

from __future__ import annotations

from pathlib import Path

# Single source of truth for the state directory name
STATE_DIR_NAME = ".bengal"


class BengalPaths:
    """
    Accessor for all .bengal directory paths.

    Provides a unified interface for accessing all paths within the
    Bengal state directory. Use this class instead of hardcoding
    ".bengal" strings throughout the codebase.

    Attributes:
        root: Project root path
        state_dir: Path to .bengal directory

    Example:
        >>> paths = BengalPaths(Path("/my/site"))
        >>> paths.build_cache
        PosixPath('/my/site/.bengal/cache.json')
        >>> paths.logs_dir
        PosixPath('/my/site/.bengal/logs')
    """

    def __init__(self, root: Path) -> None:
        """
        Initialize BengalPaths with project root.

        Args:
            root: Path to project root directory
        """
        self.root = root
        self.state_dir = root / STATE_DIR_NAME

    # =========================================================================
    # BUILD CACHES
    # =========================================================================

    @property
    def build_cache(self) -> Path:
        """Main build cache file (.bengal/cache.json)."""
        return self.state_dir / "cache.json"

    @property
    def page_cache(self) -> Path:
        """Page discovery cache file (.bengal/page_metadata.json)."""
        return self.state_dir / "page_metadata.json"

    @property
    def asset_cache(self) -> Path:
        """Asset dependency map file (.bengal/asset_deps.json)."""
        return self.state_dir / "asset_deps.json"

    @property
    def taxonomy_cache(self) -> Path:
        """Taxonomy index cache file (.bengal/taxonomy_index.json)."""
        return self.state_dir / "taxonomy_index.json"

    # =========================================================================
    # INDEXES
    # =========================================================================

    @property
    def indexes_dir(self) -> Path:
        """Query indexes directory (.bengal/indexes/)."""
        return self.state_dir / "indexes"

    # =========================================================================
    # TEMPLATES
    # =========================================================================

    @property
    def templates_dir(self) -> Path:
        """Jinja bytecode cache directory (.bengal/templates/)."""
        return self.state_dir / "templates"

    # =========================================================================
    # CONTENT
    # =========================================================================

    @property
    def content_dir(self) -> Path:
        """Remote content cache directory (.bengal/content_cache/)."""
        return self.state_dir / "content_cache"

    @property
    def generated_dir(self) -> Path:
        """Generated content directory (.bengal/generated/)."""
        return self.state_dir / "generated"

    # =========================================================================
    # LOGS & METRICS
    # =========================================================================

    @property
    def logs_dir(self) -> Path:
        """Logs directory (.bengal/logs/)."""
        return self.state_dir / "logs"

    @property
    def build_log(self) -> Path:
        """Build log file (.bengal/logs/build.log)."""
        return self.logs_dir / "build.log"

    @property
    def serve_log(self) -> Path:
        """Serve log file (.bengal/logs/serve.log)."""
        return self.logs_dir / "serve.log"

    @property
    def metrics_dir(self) -> Path:
        """Performance metrics directory (.bengal/metrics/)."""
        return self.state_dir / "metrics"

    @property
    def profiles_dir(self) -> Path:
        """Profiling output directory (.bengal/profiles/)."""
        return self.state_dir / "profiles"

    # =========================================================================
    # HISTORY & STATE
    # =========================================================================

    @property
    def build_history(self) -> Path:
        """Build history file (.bengal/build_history.json)."""
        return self.state_dir / "build_history.json"

    @property
    def server_pid(self) -> Path:
        """Server PID file (.bengal/server.pid)."""
        return self.state_dir / "server.pid"

    @property
    def asset_manifest(self) -> Path:
        """Asset manifest file (.bengal/asset-manifest.json)."""
        return self.state_dir / "asset-manifest.json"

    # =========================================================================
    # THEMES
    # =========================================================================

    @property
    def themes_dir(self) -> Path:
        """Theme state directory (.bengal/themes/)."""
        return self.state_dir / "themes"

    @property
    def swizzle_registry(self) -> Path:
        """Swizzle registry file (.bengal/themes/sources.json)."""
        return self.themes_dir / "sources.json"

    # =========================================================================
    # TEMPORARY FILES
    # =========================================================================

    @property
    def js_bundle_dir(self) -> Path:
        """JS bundle temporary directory (.bengal/js_bundle/)."""
        return self.state_dir / "js_bundle"

    @property
    def pipeline_out_dir(self) -> Path:
        """Asset pipeline temporary output directory (.bengal/pipeline_out/)."""
        return self.state_dir / "pipeline_out"

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def ensure_dirs(self) -> None:
        """
        Create all necessary directories.

        Safe to call multiple times - uses exist_ok=True.
        Does not create file paths, only directories.
        """
        dirs = [
            self.state_dir,
            self.indexes_dir,
            self.templates_dir,
            self.content_dir,
            self.generated_dir,
            self.logs_dir,
            self.metrics_dir,
            self.profiles_dir,
            self.themes_dir,
            self.js_bundle_dir,
            self.pipeline_out_dir,
        ]
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"BengalPaths(root={self.root})"


def migrate_template_cache(paths: BengalPaths, output_dir: Path) -> bool:
    """
    Migrate template cache from old location to new location.

    Old location: output_dir/.bengal-cache/templates/
    New location: .bengal/templates/

    Args:
        paths: BengalPaths instance for the site
        output_dir: Output directory (e.g., public/)

    Returns:
        True if migration was performed, False if not needed
    """
    import shutil

    old_cache = output_dir / ".bengal-cache" / "templates"

    if not old_cache.exists():
        return False

    if paths.templates_dir.exists() and any(paths.templates_dir.iterdir()):
        # New location already has content, don't overwrite
        # Just clean up old location
        try:
            shutil.rmtree(old_cache)
            # Remove parent if empty
            old_parent = output_dir / ".bengal-cache"
            if old_parent.exists() and not any(old_parent.iterdir()):
                old_parent.rmdir()
        except Exception:
            pass
        return False

    # Migrate cache to new location
    try:
        paths.templates_dir.mkdir(parents=True, exist_ok=True)
        for item in old_cache.iterdir():
            shutil.move(str(item), str(paths.templates_dir / item.name))

        # Clean up old directory
        shutil.rmtree(old_cache)

        # Remove parent if empty
        old_parent = output_dir / ".bengal-cache"
        if old_parent.exists() and not any(old_parent.iterdir()):
            old_parent.rmdir()

        return True
    except Exception:
        return False
