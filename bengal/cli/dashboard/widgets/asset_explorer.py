"""
Asset Explorer Widget.

Filterable asset list grouped by type.
Displays images, stylesheets, scripts, and other assets.

Usage:
    from bengal.cli.dashboard.widgets import AssetExplorer

    explorer = AssetExplorer()
    explorer.set_site(site)

RFC: rfc-dashboard-api-integration
"""

from __future__ import annotations

import contextlib
from collections import defaultdict
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Static, TabbedContent, TabPane

if TYPE_CHECKING:
    from bengal.core.asset import Asset
    from bengal.core.site import Site


# Asset type categorization
ASSET_CATEGORIES: dict[str, set[str]] = {
    "images": {"jpg", "jpeg", "png", "gif", "webp", "svg", "ico", "avif"},
    "styles": {"css", "scss", "sass", "less"},
    "scripts": {"js", "ts", "mjs", "cjs"},
    "fonts": {"woff", "woff2", "ttf", "otf", "eot"},
    "data": {"json", "yaml", "yml", "xml", "csv"},
    "media": {"mp4", "webm", "mp3", "wav", "ogg"},
}

CATEGORY_ICONS: dict[str, str] = {
    "images": "🖼️",
    "styles": "🎨",
    "scripts": "📜",
    "fonts": "🔤",
    "data": "📊",
    "media": "🎬",
    "other": "📎",
}


def categorize_asset(asset: Asset) -> str:
    """Determine asset category from file extension."""
    ext = asset.source_path.suffix.lstrip(".").lower() if asset.source_path else ""
    for category, extensions in ASSET_CATEGORIES.items():
        if ext in extensions:
            return category
    return "other"


class AssetExplorer(Vertical):
    """
    Tabbed asset browser grouped by type.

    Features:
    - Tabs for each asset category (images, styles, scripts, etc.)
    - DataTable with asset details (name, size, path)
    - Size summary per category
    - Quick filter within tabs

    Example:
        explorer = AssetExplorer(id="asset-explorer")
        explorer.set_site(site)

    """

    DEFAULT_CSS = """
    AssetExplorer {
        height: 100%;
        border: solid $primary;
    }
    AssetExplorer .explorer-header {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    AssetExplorer TabbedContent {
        height: 1fr;
    }
    AssetExplorer DataTable {
        height: 100%;
    }
    """

    total_assets: reactive[int] = reactive(0)
    total_size_bytes: reactive[int] = reactive(0)

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize asset explorer."""
        super().__init__(id=id, classes=classes)
        self._site: Site | None = None
        self._categorized: dict[str, list[Asset]] = defaultdict(list)

    def compose(self) -> ComposeResult:
        """Compose the asset explorer."""
        yield Static(
            self._format_header(),
            classes="explorer-header",
            id="asset-header",
        )

        with TabbedContent(id="asset-tabs"):
            for category in ["images", "styles", "scripts", "fonts", "data", "media", "other"]:
                icon = CATEGORY_ICONS.get(category, "📎")
                with TabPane(f"{icon} {category.title()}", id=f"tab-{category}"):
                    table = DataTable(id=f"table-{category}")
                    table.add_columns("Name", "Size", "Path")
                    yield table

    def set_site(self, site: Site) -> None:
        """
        Populate the explorer from a Site object.

        Args:
            site: Site instance with assets
        """
        self._site = site
        self._rebuild_tables()

    def _rebuild_tables(self) -> None:
        """Rebuild all asset tables from current site data."""
        if self._site is None:
            return

        # Categorize all assets
        self._categorized = defaultdict(list)
        total_size = 0

        for asset in self._site.assets:
            category = categorize_asset(asset)
            self._categorized[category].append(asset)
            # Get file size if available
            if asset.source_path and asset.source_path.exists():
                with contextlib.suppress(OSError):
                    total_size += asset.source_path.stat().st_size

        # Update tables
        for category in ["images", "styles", "scripts", "fonts", "data", "media", "other"]:
            table = self.query_one(f"#table-{category}", DataTable)
            table.clear()

            assets = self._categorized.get(category, [])
            for asset in sorted(assets, key=lambda a: str(a.source_path)):
                name = asset.source_path.name if asset.source_path else "?"
                size = self._format_size(asset)
                path = str(asset.source_path.parent) if asset.source_path else ""
                table.add_row(name, size, path)

        # Update stats
        self.total_assets = len(self._site.assets)
        self.total_size_bytes = total_size

        # Update header
        header = self.query_one("#asset-header", Static)
        header.update(self._format_header())

    def _format_size(self, asset: Asset) -> str:
        """Format asset file size."""
        if not asset.source_path or not asset.source_path.exists():
            return "?"
        try:
            size = asset.source_path.stat().st_size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size // 1024} KB"
            else:
                return f"{size // (1024 * 1024):.1f} MB"
        except OSError:
            return "?"

    def _format_header(self) -> str:
        """Format header with total stats."""
        if self.total_size_bytes < 1024 * 1024:
            size_str = f"{self.total_size_bytes // 1024} KB"
        else:
            size_str = f"{self.total_size_bytes / (1024 * 1024):.1f} MB"
        return f"📦 Assets ({self.total_assets} files, {size_str})"

    def refresh_from_site(self) -> None:
        """Refresh data from current site."""
        if self._site is not None:
            self._rebuild_tables()
