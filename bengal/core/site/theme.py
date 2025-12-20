"""
Theme integration mixin for Site.

Provides methods for theme resolution and asset chain discovery.

Related Modules:
    - bengal.core.site.core: Main Site dataclass using this mixin
    - bengal.core.theme: Theme configuration
    - bengal.utils.theme_resolution: Theme inheritance chain resolution
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    pass


class ThemeIntegrationMixin:
    """
    Mixin providing theme integration methods.

    Requires these attributes on the host class:
        - root_path: Path
        - theme: str | None
    """

    # Type hints for mixin attributes (provided by host class)
    root_path: Path
    theme: str | None

    def _get_theme_assets_dir(self) -> Path | None:
        """
        Get the assets directory for the current theme.

        Searches for theme assets in order:
        1. Site's themes directory (site/themes/{theme}/assets)
        2. Bengal's bundled themes (bengal/themes/{theme}/assets)

        Returns:
            Path to theme assets directory, or None if theme not found or
            assets directory doesn't exist

        See Also:
            _get_theme_assets_chain(): Gets complete inheritance chain of asset directories
        """
        if not self.theme:
            return None

        # Check in site's themes directory first
        site_theme_dir = self.root_path / "themes" / self.theme / "assets"
        if site_theme_dir.exists():
            return site_theme_dir

        # Check in Bengal's bundled themes
        import bengal

        bengal_dir = Path(bengal.__file__).parent
        bundled_theme_dir = bengal_dir / "themes" / self.theme / "assets"
        if bundled_theme_dir.exists():
            return bundled_theme_dir

        return None

    def _get_theme_assets_chain(self) -> list[Path]:
        """
        Return list of theme asset directories from inheritance chain.

        Returns asset directories in order from parent themes to child theme
        (low → high priority). Site assets override all theme assets.

        Returns:
            List of Path objects for theme asset directories, ordered from
            parent (low priority) to child (high priority). Empty list if
            no theme assets found.

        Priority Order (lowest to highest):
            1. Default theme assets (if extended)
            2. Parent theme assets (if extended)
            3. Child theme assets
            4. Site assets (highest priority, handled separately)

        See Also:
            bengal.utils.theme_resolution: Theme inheritance chain resolution
            discover_assets(): Uses this for theme asset discovery
        """
        dirs: list[Path] = []
        try:
            from bengal.core.theme import resolve_theme_chain

            chain = resolve_theme_chain(self.root_path, self.theme)
        except Exception as e:
            emit_diagnostic(
                self,
                "debug",
                "theme_chain_resolution_failed",
                theme=self.theme,
                error=str(e),
            )
            chain = [self.theme] if self.theme else []

        for theme_name in reversed(chain):
            from bengal.core.theme import iter_theme_asset_dirs

            for d in iter_theme_asset_dirs(self.root_path, [theme_name]):
                dirs.append(d)
        return dirs
