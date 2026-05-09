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
            attrs = _render_tag_attrs(asset.tag_attrs)
            if asset.asset_type == "css":
                lines.append(f'<link rel="stylesheet" href="{url}"{attrs}>')
            elif asset.asset_type == "javascript":
                lines.append(f'<script src="{url}"{attrs}></script>')
    return Markup("\n".join(lines))


def _render_tag_attrs(attrs: tuple[tuple[str, str | bool], ...]) -> str:
    """Render normalized HTML attributes with escaping."""
    parts: list[str] = []
    for name, value in attrs:
        escaped_name = escape(name, quote=True)
        if value is True:
            parts.append(f" {escaped_name}")
        elif value is False:
            continue
        else:
            escaped_value = escape(value, quote=True)
            parts.append(f' {escaped_name}="{escaped_value}"')
    return "".join(parts)


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
