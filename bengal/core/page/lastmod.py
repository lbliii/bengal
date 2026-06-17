"""Last-modified resolution for pages (frontmatter, git, file mtime)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.protocols import PageLike


def resolve_page_lastmod(
    page: PageLike, git_dates: dict[Path, datetime] | None = None
) -> datetime | None:
    """
    Resolve a page's last-modified timestamp.

    Precedence:
    1. Frontmatter ``lastmod`` / ``last_modified`` / ``updated``
    2. Git commit date (when ``git_dates`` supplies the source path)
    3. Source file mtime
    """
    metadata = getattr(page, "metadata", {}) or {}
    for key in ("lastmod", "last_modified", "updated"):
        if value := metadata.get(key):
            parsed = _coerce_datetime(value)
            if parsed is not None:
                return parsed

    source_path = getattr(page, "source_path", None)
    if source_path and git_dates:
        git_date = git_dates.get(source_path.resolve())
        if git_date is not None:
            return git_date

    if source_path:
        try:
            return datetime.fromtimestamp(source_path.stat().st_mtime)
        except OSError:
            pass

    return None


def resolve_page_lastmod_iso(
    page: PageLike,
    git_dates: dict[Path, datetime] | None = None,
) -> str | None:
    """Return ISO 8601 last-modified string for a page, if available."""
    lastmod = resolve_page_lastmod(page, git_dates=git_dates)
    if lastmod is None:
        return None
    return lastmod.isoformat()


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return datetime.fromisoformat(value.isoformat())
        except TypeError, ValueError:
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None
