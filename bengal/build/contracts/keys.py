"""
Canonical cache key generation.

ALL cache operations MUST use these functions for path keys.
This ensures consistent lookup regardless of how paths arrive
(absolute, relative, with/without prefix).
"""

from __future__ import annotations

from pathlib import Path
from typing import NewType

from bengal.utils.paths.normalize import to_posix

# Type-safe cache key - prevents accidental str mixing
CacheKey = NewType("CacheKey", str)


def content_key(path: Path, site_root: Path) -> CacheKey:
    """
    Canonical key for content files (pages, sections).

    Always relative to site root, forward slashes, no leading dot.

    Examples:
        content_key(Path("/site/content/about.md"), Path("/site"))
        → "content/about.md"
    """
    try:
        rel = path.resolve().relative_to(site_root.resolve())
        return CacheKey(to_posix(rel))
    except ValueError:
        # External path - use resolved absolute
        return CacheKey(to_posix(path.resolve()))


def data_key(path: Path, site_root: Path) -> CacheKey:
    """
    Canonical key for data files.

    Prefixed with "data:" to distinguish from content.

    Examples:
        data_key(Path("/site/data/team.yaml"), Path("/site"))
        → "data:data/team.yaml"
    """
    rel = content_key(path, site_root)
    return CacheKey(f"data:{rel}")


def template_key(path: Path, templates_dir: Path) -> CacheKey:
    """Canonical key for template files."""
    try:
        rel = path.resolve().relative_to(templates_dir.resolve())
        return CacheKey(to_posix(rel))
    except ValueError:
        return CacheKey(to_posix(path.resolve()))


def asset_key(path: Path, assets_dir: Path) -> CacheKey:
    """Canonical key for asset files."""
    try:
        rel = path.resolve().relative_to(assets_dir.resolve())
        return CacheKey(to_posix(rel))
    except ValueError:
        return CacheKey(to_posix(path.resolve()))


def parse_key(key: CacheKey) -> tuple[str, str]:
    """
    Parse a cache key into (prefix, path).

    Examples:
        parse_key("data:data/team.yaml") → ("data", "data/team.yaml")
        parse_key("content/about.md") → ("", "content/about.md")
    """
    if ":" in key and not key.startswith("/"):
        prefix, path = key.split(":", 1)
        return (prefix, path)
    return ("", key)
