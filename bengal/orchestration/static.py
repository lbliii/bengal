"""
Static file orchestrator - copies static/ to output verbatim.

This enables raw HTML pages, downloadable files, and other assets
that need to bypass the content pipeline while still having access
to theme assets via /assets/css/style.css.

Key Concepts:
    - Verbatim copying: Files copied as-is without processing
    - Directory preservation: Maintains directory structure from static/
    - Size warnings: Warns when static folder exceeds size threshold
    - Theme asset access: Static files can reference theme assets

Related Modules:
    - bengal.orchestration.asset: Asset processing (for theme assets)
    - bengal.core.site: Site container with static directory

Usage:
    static/demos/holo.html  → public/demos/holo.html
    static/downloads/app.pdf → public/downloads/app.pdf
    static/robots.txt        → public/robots.txt

See Also:
    - bengal/orchestration/static.py:process_static_files() for processing logic
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)

# Warn if total static folder size exceeds this (50MB)
LARGE_STATIC_WARNING_BYTES = 50 * 1024 * 1024


class StaticOrchestrator:
    """
    Orchestrates static file copying to output directory.

    Copies files from static/ directory to output directory verbatim without
    any processing. Preserves directory structure and warns about large static
    folders that might impact build performance.

    Creation:
        Direct instantiation: StaticOrchestrator(site)
            - Created by BuildOrchestrator during build
            - Requires Site instance with root_path and output_dir

    Attributes:
        site: Site instance with root_path and output_dir
        logger: Logger instance for static file operations
        static_dir: Path to static/ directory (from config or default)
        output_dir: Output directory path
        enabled: Whether static file copying is enabled

    Relationships:
        - Used by: BuildOrchestrator for static file copying phase
        - Uses: Site for directory paths and configuration

    Thread Safety:
        Thread-safe for parallel file copying operations.

    Examples:
        orchestrator = StaticOrchestrator(site)
        if orchestrator.is_enabled():
            count = orchestrator.copy()
    """

    def __init__(self, site: Site) -> None:
        self.site = site
        self.logger = get_logger(__name__)

        # Get config with defaults
        static_config = site.config.get("static", {})
        static_dir_name = static_config.get("dir", "static")

        self.static_dir = site.root_path / static_dir_name
        self.output_dir = site.output_dir
        self.enabled = static_config.get("enabled", True)

    def is_enabled(self) -> bool:
        """Check if static folder exists and is enabled."""
        return bool(self.enabled and self.static_dir.exists() and self.static_dir.is_dir())

    def get_total_size(self) -> int:
        """Calculate total size of static folder in bytes."""
        if not self.static_dir.exists():
            return 0
        return sum(f.stat().st_size for f in self.static_dir.rglob("*") if f.is_file())

    def copy(self) -> int:
        """
        Copy static files to output directory.

        Files are copied verbatim without any processing.
        Directory structure is preserved.

        Returns:
            Number of files copied
        """
        if not self.is_enabled():
            self.logger.debug("static_copy_skipped", reason="disabled_or_missing")
            return 0

        # Check for large static folder
        total_size = self.get_total_size()
        if total_size > LARGE_STATIC_WARNING_BYTES:
            size_mb = total_size / (1024 * 1024)
            self.logger.warning(
                "static_folder_large",
                size_mb=f"{size_mb:.1f}",
                hint="Consider moving large files to external storage",
            )

        count = 0
        errors = 0

        for source_path in self.static_dir.rglob("*"):
            if not source_path.is_file():
                continue

            # Compute relative path and destination
            rel_path = source_path.relative_to(self.static_dir)
            dest_path = self.output_dir / rel_path

            try:
                # Create parent directories
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file (preserving metadata)
                shutil.copy2(source_path, dest_path)
                count += 1

                self.logger.debug("static_file_copied", source=str(rel_path))

            except OSError as e:
                errors += 1
                self.logger.warning(
                    "static_file_copy_failed",
                    source=str(rel_path),
                    error=str(e),
                )

        if count > 0:
            self.logger.info("static_files_copied", count=count)

        if errors > 0:
            self.logger.warning("static_copy_errors", count=errors)

        return count

    def copy_single(self, rel_path: Path | str) -> bool:
        """
        Copy a single static file (for incremental updates).

        Args:
            rel_path: Path relative to static folder

        Returns:
            True if file was copied successfully
        """
        if not self.is_enabled():
            return False

        rel_path = Path(rel_path)
        source_path = self.static_dir / rel_path
        dest_path = self.output_dir / rel_path

        if not source_path.is_file():
            self.logger.debug("static_file_not_found", path=str(rel_path))
            return False

        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_path)
            self.logger.debug("static_file_updated", path=str(rel_path))
            return True
        except OSError as e:
            self.logger.warning(
                "static_file_copy_failed",
                path=str(rel_path),
                error=str(e),
            )
            return False

    def remove_single(self, rel_path: Path | str) -> bool:
        """
        Remove a single static file from output (when source is deleted).

        Args:
            rel_path: Path relative to static folder

        Returns:
            True if file was removed successfully
        """
        rel_path = Path(rel_path)
        dest_path = self.output_dir / rel_path

        if not dest_path.exists():
            return False

        try:
            dest_path.unlink()
            self.logger.debug("static_file_removed", path=str(rel_path))
            return True
        except OSError as e:
            self.logger.warning(
                "static_file_remove_failed",
                path=str(rel_path),
                error=str(e),
            )
            return False
