"""
Asset discovery - finds and organizes static assets.
"""

from pathlib import Path

from bengal.core.asset import Asset


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

    def discover(self) -> list[Asset]:
        """
        Discover all assets in the assets directory.

        Simply walks the directory tree and creates Asset objects.
        No business logic - just discovery.

        Returns:
            List of Asset objects
        """
        # Walk the assets directory
        for file_path in self.assets_dir.rglob("*"):
            if file_path.is_file():
                # Skip hidden files
                if any(part.startswith(".") for part in file_path.parts):
                    continue

                # Skip markdown/documentation files
                if file_path.suffix.lower() == ".md":
                    continue

                # Create asset with relative output path
                rel_path = file_path.relative_to(self.assets_dir)

                asset = Asset(
                    source_path=file_path,
                    output_path=rel_path,
                )

                self.assets.append(asset)

        return self.assets
