"""Template helpers for theme library assets."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

from kida import Markup

from bengal.rendering.assets import resolve_asset_url

if TYPE_CHECKING:
    from bengal.core.theme.providers import ThemeLibraryProvider
    from bengal.protocols import SiteLike


def render_library_asset_tags(
    providers: tuple[ThemeLibraryProvider, ...],
    site: SiteLike,
) -> Markup:
    """Render stylesheet/script tags for declared provider assets.

    Library contracts decide which browser assets are Bengal-managed. Assets in
    ``none`` mode are metadata-only and intentionally produce no tags.
    """
    lines: list[str] = []
    seen: set[str] = set()
    for provider in providers:
        for asset in provider.assets:
            if asset.mode == "none":
                continue
            logical = asset.logical_path.as_posix()
            if logical in seen:
                continue
            seen.add(logical)
            url = escape(resolve_asset_url(logical, site), quote=True)
            if asset.asset_type == "css":
                lines.append(f'<link rel="stylesheet" href="{url}">')
            elif asset.asset_type == "javascript":
                lines.append(f'<script src="{url}"></script>')
    return Markup("\n".join(lines))


def library_runtime_metadata(providers: tuple[ThemeLibraryProvider, ...]) -> tuple[str, ...]:
    """Return deduplicated runtime requirements declared by theme libraries."""
    seen: set[str] = set()
    runtime: list[str] = []
    for provider in providers:
        for item in provider.runtime:
            if item not in seen:
                seen.add(item)
                runtime.append(item)
    return tuple(runtime)
