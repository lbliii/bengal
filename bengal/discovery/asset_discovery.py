"""
Asset discovery for Bengal SSG.

This module provides the AssetDiscovery class that finds and organizes static
assets (images, CSS, JavaScript, fonts, etc.) during site builds.

Architecture:
    AssetDiscovery follows Bengal's separation of concerns:
    - Discovery ONLY finds files and creates Asset objects
    - Asset processing (optimization, bundling, minification) is handled by
      orchestrators in `bengal/orchestration/`

    The class skips hidden files, temporary files (.tmp), and markdown files
    to avoid including non-asset content.

Related:
    - bengal/core/asset.py: Asset data model
    - bengal/orchestration/asset_orchestrator.py: Asset processing
    - bengal/discovery/__init__.py: Package exports
"""

from __future__ import annotations

from pathlib import Path

from bengal.core.asset import Asset
from bengal.utils.logger import LogLevel, get_logger

logger = get_logger(__name__)


class AssetDiscovery:
    """
    Discovers static assets (images, CSS, JS, fonts, etc.).

    This class is responsible ONLY for finding files and creating Asset objects.
    Asset processing logic (bundling, minification, optimization) is handled
    by orchestrators.

    Filtering Behavior:
        - Skips hidden files and directories (starting with '.')
        - Skips temporary files (.tmp extension)
        - Skips markdown files (.md extension)
        - Creates the assets directory if it doesn't exist

    Attributes:
        assets_dir: Root directory to scan for assets
        assets: List of discovered Asset objects (populated after discover())

    Example:
        >>> from bengal.discovery import AssetDiscovery
        >>> from pathlib import Path
        >>>
        >>> discovery = AssetDiscovery(Path("static"))
        >>> assets = discovery.discover()
        >>> for asset in assets:
        ...     print(f"{asset.source_path} -> {asset.output_path}")
    """

    def __init__(self, assets_dir: Path) -> None:
        """
        Initialize asset discovery.

        Args:
            assets_dir: Root directory containing static assets
        """
        self.assets_dir = assets_dir
        self.assets: list[Asset] = []

    def discover(self, base_path: Path | None = None) -> list[Asset]:
        """
        Discover all static assets in the assets directory.

        Recursively walks the assets directory and creates Asset objects for
        each file found. Skips hidden files, temporary files, and markdown files.

        Args:
            base_path: Optional override for the assets directory. If None,
                uses self.assets_dir.

        Returns:
            List of Asset objects with source_path and output_path set.
            Also populates self.assets with the same list.

        Note:
            If the assets directory doesn't exist, it is created automatically.
            Small assets (< 1KB) are logged at DEBUG level for visibility.
        """
        # Use provided assets dir or fall back to self.assets_dir
        assets_dir = self.assets_dir if base_path is None else base_path
        if not assets_dir.exists():
            assets_dir.mkdir(parents=True, exist_ok=True)

        # Walk the assets directory
        for file_path in assets_dir.rglob("*"):
            if file_path.is_file():
                # Skip hidden files
                if any(part.startswith(".") for part in file_path.parts):
                    continue

                # Skip temporary files (from atomic writes and image optimization)
                if file_path.suffix.lower() == ".tmp":
                    continue

                # Skip markdown/documentation files
                if file_path.suffix.lower() == ".md":
                    continue

                # Create asset with relative output path
                rel_path = file_path.relative_to(assets_dir)

                asset = Asset(
                    source_path=file_path,
                    output_path=rel_path,
                )

                self.assets.append(asset)

        # Validate assets (debug-level only). Avoid stat() calls when debug is not enabled.
        if logger.level.value <= LogLevel.DEBUG.value:
            for asset in self.assets:
                try:
                    size = Path(asset.source_path).stat().st_size
                    if size < 1000:
                        # Small assets (favicons, icons, etc.) are perfectly normal
                        logger.debug(
                            "small_asset_discovered", path=str(asset.source_path), size_bytes=size
                        )
                except (AttributeError, FileNotFoundError):
                    # This indicates a bug in asset creation - log as warning
                    logger.warning("asset_missing_path", asset=str(asset))
        return self.assets
