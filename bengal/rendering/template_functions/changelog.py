"""
Changelog view filters for templates.

Provides normalized ReleaseView dataclass and `releases` filter to unify
data-driven (changelog.yaml) and page-driven (individual markdown files)
changelog modes.

Example:
    {% for rel in section | releases %}
      <h2>{{ rel.version }}</h2>
      <span>{{ rel.date }}</span>
      {% if rel.added %}
        <h3>✨ Added</h3>
        <ul>{% for item in rel.added %}<li>{{ item }}</li>{% end %}</ul>
      {% end %}
    {% end %}
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.rendering.engines.protocol import TemplateEnvironment


@dataclass(frozen=True, slots=True)
class ReleaseView:
    """
    Normalized view of a changelog release for templates.
    
    Unifies data-driven (from changelog.yaml) and page-driven (from markdown
    files) releases into a single consistent interface.
    
    Attributes:
        version: Version string (e.g., "1.2.0")
        name: Release name/codename
        date: Release date (string or datetime)
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
    date: str | datetime | None
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
            date=release.get("date"),
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

        return cls(
            version=version,
            name=metadata.get("name") or "",
            date=getattr(page, "date", None),
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


def releases_filter(source: Any) -> list[ReleaseView]:
    """
    Convert releases from data or pages to normalized ReleaseView objects.
    
    Handles both modes:
    - Data-driven: Pass site.data.changelog.releases
    - Page-driven: Pass section.pages or pages list
    
    Args:
        source: List of release dicts or Page objects
    
    Returns:
        List of ReleaseView objects
    
    Example (data-driven):
        {% let changelog = site.data.changelog %}
        {% for rel in changelog.releases | releases %}
          {{ rel.version }}
        {% end %}
    
    Example (page-driven):
        {% for rel in pages | releases %}
          {{ rel.version }}
        {% end %}
        
    """
    if not source:
        return []

    result = []
    for item in source:
        try:
            if isinstance(item, dict):
                # Data-driven mode
                result.append(ReleaseView.from_data(item))
            else:
                # Page-driven mode
                result.append(ReleaseView.from_page(item))
        except Exception:
            # Skip items that can't be converted
            continue

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
