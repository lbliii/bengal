"""
Asset discovery - finds and organizes static assets.
"""

from pathlib import Path

from bengal.core.asset import Asset
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class AssetDiscovery:
    """
    Discovers static assets (images, CSS, JS, etc.).

    This class is responsible ONLY for finding files.
    Asset processing logic (bundling, minification) is handled elsewhere.
    """

    def __init__(self, assets_dir: Path) -> None:
        """
        Initialize asset discovery.

        Args:
            assets_dir: Root assets directory
        """
        self.assets_dir = assets_dir
        self.assets: list[Asset] = []

    def discover(self, base_path: Path | None = None) -> list:
        if base_path is None:
            base_path = self.assets_dir
        # If the base_path ends with 'assets', use it directly (theme case)
        # Otherwise, append 'assets' subdirectory (site root case)
        assets_dir = base_path if base_path.name == "assets" else base_path / "assets"
        if not assets_dir.exists():
            assets_dir.mkdir(parents=True, exist_ok=True)  # Auto-create
            # Log: "Created missing assets dir"

        # Walk the assets directory
        for file_path in assets_dir.rglob("*"):
            if file_path.is_file():
                # Skip hidden files
                if any(part.startswith(".") for part in file_path.parts):
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

        # Validate warning-only
        for asset in self.assets:
            try:
                if Path(asset.source_path).stat().st_size < 1000:
                    logger.warning(f"Small asset: {asset.source_path}")
            except (AttributeError, FileNotFoundError):
                logger.warning(f"Asset without valid path: {asset}")
        return self.assets
