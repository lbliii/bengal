"""
Changelog view filters for templates.

Provides normalized ReleaseView dataclass and `releases` filter to unify
data-driven (changelog.yaml) and page-driven (individual markdown files)
changelog modes.

Design Principle:
    **Simple, predictable defaults.** The `releases` filter always sorts
    by date (newest first) by default. This "just works" for the 99% case
    and matches what users expect from changelog pages.
    
    For custom ordering, use `releases(false)` to preserve input order.

Example:
    {# Standard usage - newest first, no thinking required #}
    {% for rel in pages | releases %}
      <h2>{{ rel.version }}</h2>
      <span>{{ rel.date }}</span>
    {% end %}
    
    {# Custom order - explicit opt-out #}
    {% for rel in pages | releases(false) | sort_by('version') %}
      ...
    {% end %}
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.rendering.engines.protocol import TemplateEnvironment

logger = get_logger(__name__)


def _normalize_date(value: Any) -> datetime | None:
    """
    Normalize a date value to datetime for reliable sorting.
    
    Handles:
    - datetime objects (returned as-is)
    - date objects (converted to datetime at midnight)
    - ISO format strings (parsed)
    - None (returned as-is)
    
    Returns:
        datetime object or None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # Handle date objects (from YAML)
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return datetime(value.year, value.month, value.day)
    # Handle string dates
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            # Try common formats
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%B %d, %Y"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            logger.debug("date_parse_failed", value=value)
            return None
    return None


@dataclass(frozen=True, slots=True)
class ReleaseView:
    """
    Normalized view of a changelog release for templates.
    
    Unifies data-driven (from changelog.yaml) and page-driven (from markdown
    files) releases into a single consistent interface.
    
    Attributes:
        version: Version string (e.g., "1.2.0")
        name: Release name/codename
        date: Release date (always datetime for reliable sorting, or None)
        status: Release status (stable, beta, rc, deprecated)
        href: URL to release page (if page-driven)
        summary: Brief release summary
        added: List of added features
        changed: List of changes
        fixed: List of bug fixes
        deprecated: List of deprecated features
        removed: List of removed features
        security: List of security fixes
        breaking: List of breaking changes
        has_structured_changes: Whether release has categorized changes
        change_types: List of change type names present
        
    """

    version: str
    name: str
    date: datetime | None  # Always datetime for reliable sorting
    status: str
    href: str
    summary: str
    added: tuple[str, ...]
    changed: tuple[str, ...]
    fixed: tuple[str, ...]
    deprecated: tuple[str, ...]
    removed: tuple[str, ...]
    security: tuple[str, ...]
    breaking: tuple[str, ...]
    has_structured_changes: bool
    change_types: tuple[str, ...]

    @classmethod
    def from_data(cls, release: dict[str, Any]) -> ReleaseView:
        """
        Create a ReleaseView from a data-driven release dict.

        Typically from changelog.yaml with structure:
            - version: "1.2.0"
              date: "2024-01-15"
              added: ["Feature 1", "Feature 2"]

        Args:
            release: Release dict from data file

        Returns:
            Normalized ReleaseView instance
        """
        # Extract change lists with safe defaults
        added = _to_tuple(release.get("added"))
        changed = _to_tuple(release.get("changed"))
        fixed = _to_tuple(release.get("fixed"))
        deprecated = _to_tuple(release.get("deprecated"))
        removed = _to_tuple(release.get("removed"))
        security = _to_tuple(release.get("security"))
        breaking = _to_tuple(release.get("breaking"))

        # Determine which change types are present
        change_types = []
        if added:
            change_types.append("added")
        if changed:
            change_types.append("changed")
        if fixed:
            change_types.append("fixed")
        if deprecated:
            change_types.append("deprecated")
        if removed:
            change_types.append("removed")
        if security:
            change_types.append("security")
        if breaking:
            change_types.append("breaking")

        has_structured = bool(change_types)

        return cls(
            version=release.get("version") or "Unknown",
            name=release.get("name") or "",
            date=_normalize_date(release.get("date")),
            status=release.get("status") or "",
            href=release.get("url") or release.get("href") or "",
            summary=release.get("summary") or release.get("description") or "",
            added=added,
            changed=changed,
            fixed=fixed,
            deprecated=deprecated,
            removed=removed,
            security=security,
            breaking=breaking,
            has_structured_changes=has_structured,
            change_types=tuple(change_types),
        )

    @classmethod
    def from_page(cls, page: Any) -> ReleaseView:
        """
        Create a ReleaseView from a page-driven release.

        Extracts release metadata from page frontmatter:
            ---
            title: "v1.2.0"
            date: 2024-01-15
            added:
              - "Feature 1"
            ---

        Args:
            page: Page object representing a release

        Returns:
            Normalized ReleaseView instance
        """
        # Get metadata safely
        metadata = getattr(page, "metadata", None) or {}
        if not hasattr(metadata, "get"):
            metadata = {}

        # Extract change lists
        added = _to_tuple(metadata.get("added"))
        changed = _to_tuple(metadata.get("changed"))
        fixed = _to_tuple(metadata.get("fixed"))
        deprecated = _to_tuple(metadata.get("deprecated"))
        removed = _to_tuple(metadata.get("removed"))
        security = _to_tuple(metadata.get("security"))
        breaking = _to_tuple(metadata.get("breaking"))

        # Determine which change types are present
        change_types = []
        if added:
            change_types.append("added")
        if changed:
            change_types.append("changed")
        if fixed:
            change_types.append("fixed")
        if deprecated:
            change_types.append("deprecated")
        if removed:
            change_types.append("removed")
        if security:
            change_types.append("security")
        if breaking:
            change_types.append("breaking")

        has_structured = bool(change_types)

        # Version: from title or metadata
        version = metadata.get("version") or getattr(page, "title", None) or "Unknown"

        # Summary: from description, summary, or excerpt
        summary = (
            metadata.get("description")
            or metadata.get("summary")
            or getattr(page, "excerpt", None)
            or ""
        )

        # Get date from page (already a datetime from Page.date property)
        page_date = getattr(page, "date", None)

        return cls(
            version=version,
            name=metadata.get("name") or "",
            date=_normalize_date(page_date),
            status=metadata.get("status") or "",
            href=getattr(page, "href", None) or "#",
            summary=summary,
            added=added,
            changed=changed,
            fixed=fixed,
            deprecated=deprecated,
            removed=removed,
            security=security,
            breaking=breaking,
            has_structured_changes=has_structured,
            change_types=tuple(change_types),
        )


def _to_tuple(value: Any) -> tuple[str, ...]:
    """Convert a list/iterable to a tuple of strings, or empty tuple."""
    if not value:
        return ()
    if isinstance(value, str):
        return (value,)
    try:
        return tuple(str(item) for item in value)
    except (TypeError, ValueError):
        return ()


def _sort_releases(releases: list[ReleaseView]) -> list[ReleaseView]:
    """
    Sort releases by date (newest first), then version (descending).
    
    Matches ChangelogStrategy's sorting logic so results are consistent
    whether releases come from pages or YAML data.
    
    None dates are placed at the end to keep dated releases prominent.
    """
    # Partition into dated and undated
    with_date = [r for r in releases if r.date is not None]
    without_date = [r for r in releases if r.date is None]
    
    # Sort dated releases: by date desc, then version desc (matches ChangelogStrategy)
    sorted_with_date = sorted(
        with_date,
        key=lambda r: (r.date, r.version),
        reverse=True,
    )
    
    # Undated releases go at the end, sorted by version desc
    sorted_without_date = sorted(without_date, key=lambda r: r.version, reverse=True)
    
    return sorted_with_date + sorted_without_date


def releases_filter(source: Any, sorted: bool = True) -> list[ReleaseView]:
    """
    Convert releases to normalized ReleaseView objects, sorted newest-first.
    
    By default, releases are **always sorted** by date (newest first), then
    by version for same-day releases. This provides predictable, ergonomic
    behavior for both theme developers and content writers.
    
    Args:
        source: List of release dicts (from YAML) or Page objects (from section)
        sorted: Sort by date newest-first (default: True). Set to False to
                preserve input order for custom sorting.
    
    Returns:
        List of ReleaseView objects, sorted newest-first by default
    
    Example (standard usage - newest first):
        {% for rel in pages | releases %}
          {{ rel.version }} - {{ rel.date }}
        {% end %}
    
    Example (preserve input order for custom sorting):
        {% let custom_order = pages | releases(false) | sort_by('version') %}
        
    """
    if not source:
        return []

    result = []
    for item in source:
        try:
            if isinstance(item, dict):
                result.append(ReleaseView.from_data(item))
            else:
                result.append(ReleaseView.from_page(item))
        except Exception as e:
            logger.debug("release_conversion_failed", error=str(e))
            continue

    if sorted:
        result = _sort_releases(result)

    return result


def release_view_filter(item: Any) -> ReleaseView | None:
    """
    Convert a single release item to a ReleaseView.
    
    Args:
        item: Release dict or Page object
    
    Returns:
        ReleaseView object or None if conversion fails
    
    Example:
        {% let rel = release | release_view %}
        <h2>{{ rel.version }}</h2>
        
    """
    if not item:
        return None

    try:
        if isinstance(item, dict):
            return ReleaseView.from_data(item)
        else:
            return ReleaseView.from_page(item)
    except Exception:
        return None


def register(env: TemplateEnvironment, site: Site) -> None:
    """Register changelog view filters with template environment."""
    env.filters.update(
        {
            "releases": releases_filter,
            "release_view": release_view_filter,
        }
    )
