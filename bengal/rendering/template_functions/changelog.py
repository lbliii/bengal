"""
Changelog view filters for templates.

Provides normalized ReleaseView dataclass and `releases` filter to unify
data-driven (changelog.yaml) and page-driven (individual markdown files)
changelog modes.

Smart Version Detection:
    The filter intelligently extracts version from multiple sources:
    
    1. Explicit `version` field in frontmatter (highest priority)
    2. Filename if versioned (e.g., `0.1.8.md` → "0.1.8")
    3. Version pattern in title (e.g., "Bengal 0.1.8" → "0.1.8")
    4. Full title as fallback
    
    Supports semver (0.1.8, 1.0.0-beta) and date versioning (26.01).

Sorting:
    Releases are sorted by **version** using semantic comparison, so
    "0.1.10" correctly comes before "0.1.9". Same-version releases
    fall back to date sorting.
    
    Use `releases(false)` to preserve input order for custom sorting.

Example:
    {# Standard - sorted by version, highest first #}
    {% for rel in pages | releases %}
      <h2>{{ rel.version }}</h2>
    {% end %}
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.protocols import TemplateEnvironment

logger = get_logger(__name__)


import re

# Pattern for semantic version: 0.1.8, v1.2.3, 1.0.0-beta, etc.
_SEMVER_PATTERN = re.compile(
    r'^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[.-](.+))?$',
    re.IGNORECASE
)

# Pattern for date-based version: 26.01, 2026.01, etc.
_DATEVER_PATTERN = re.compile(
    r'^(\d{2,4})[.-](\d{1,2})(?:[.-](\d{1,2}))?$'
)


def _extract_version(text: str) -> str | None:
    """
    Extract a version string from text (title, filename, etc.).
    
    Recognizes:
    - Semver: "0.1.8", "v1.2.3", "1.0.0-beta"
    - Date versions: "26.01", "2026.01.12"
    - Prefixed: "Bengal 0.1.8" → "0.1.8"
    
    Returns None if no version pattern found.
    """
    if not isinstance(text, (str, bytes)):
        return None

    # Try direct match first
    if _SEMVER_PATTERN.match(text) or _DATEVER_PATTERN.match(text):
        return text.lstrip('v').lstrip('V')
    
    # Look for version embedded in text (e.g., "Bengal 0.1.8")
    # Search for semver-like pattern anywhere in the text
    match = re.search(r'v?(\d+\.\d+(?:\.\d+)?(?:[.-][a-zA-Z0-9]+)?)', text)
    if match:
        return match.group(1)
    
    return None


def _version_sort_key(version: str) -> tuple:
    """
    Parse version string into tuple for proper numeric sorting.
    
    Handles:
    - Semantic versioning: "1.2.3", "0.1.10", "2.0.0-beta"
    - Date versioning: "26.01", "2026.01.12"
    
    Examples:
        "0.1.9"  → (0, 1, 9, True, "")     # Stable
        "0.1.10" → (0, 1, 10, True, "")    # 10 > 9 numerically
        "1.0.0-beta" → (1, 0, 0, False, "beta")  # Prerelease
    """
    # Try semver pattern
    match = _SEMVER_PATTERN.match(version)
    if match:
        major = int(match.group(1)) if match.group(1) else 0
        minor = int(match.group(2)) if match.group(2) else 0
        patch = int(match.group(3)) if match.group(3) else 0
        suffix = match.group(4) or ""
        # Stable (no suffix) sorts before prerelease
        is_stable = suffix == ""
        return (major, minor, patch, is_stable, suffix)
    
    # Try date-based pattern (26.01 = year 26, month 01)
    match = _DATEVER_PATTERN.match(version)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3)) if match.group(3) else 0
        return (year, month, day, True, "")
    
    # Fallback: use string as-is (will sort lexically)
    return (0, 0, 0, False, version)


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

        Version extraction priority:
            1. Explicit metadata.version field
            2. Filename if it's a version (e.g., "0.1.8.md")
            3. Version extracted from title (e.g., "Bengal 0.1.8" → "0.1.8")
            4. Full title as fallback

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

        # Version extraction with smart priority:
        # 1. Explicit metadata.version (highest priority)
        # 2. Filename if it looks like a version (e.g., "0.1.8.md")
        # 3. Extract version from title (e.g., "Bengal 0.1.8" → "0.1.8")
        # 4. Full title as fallback
        version = None
        title = getattr(page, "title", None) or "Unknown"
        
        # Priority 1: Explicit version in metadata
        if metadata.get("version"):
            version = metadata["version"]
        
        # Priority 2: Filename is a version (e.g., "0.1.8.md" → "0.1.8")
        if not version:
            source_path = getattr(page, "source_path", None)
            if source_path:
                # Get filename without extension
                filename = source_path.stem if hasattr(source_path, "stem") else str(source_path).rsplit("/", 1)[-1].rsplit(".", 1)[0]
                # Check if filename IS a version (not _index, not a regular name)
                if filename and filename not in ("_index", "index"):
                    extracted = _extract_version(filename)
                    if extracted:
                        version = extracted
        
        # Priority 3: Extract version from title (e.g., "Bengal 0.1.8" → "0.1.8")
        if not version:
            extracted = _extract_version(title)
            if extracted:
                version = extracted
        
        # Priority 4: Full title as fallback
        if not version:
            version = title

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
    Sort releases by version (highest first) using semantic comparison.
    
    Version is the primary sort key because version IS the release identity.
    Date is secondary (for same-version edge cases).
    
    Uses proper numeric comparison so "0.1.10" > "0.1.9" > "0.1.2".
    Stable versions sort before prereleases: "1.0.0" > "1.0.0-beta".
    
    Sort order:
        1. By version (highest first, semantic comparison)
        2. For same version: by date (newest first)
    """
    return sorted(
        releases,
        key=lambda r: (
            _version_sort_key(r.version),
            r.date or datetime.min,  # Dated releases before undated
        ),
        reverse=True,
    )


def releases_filter(source: Any, sorted: bool = True) -> list[ReleaseView]:
    """
    Convert releases to normalized ReleaseView objects, sorted by version.
    
    By default, releases are **sorted by version** (highest first) using
    semantic comparison. This means "0.1.10" correctly comes before "0.1.9".
    
    Version is extracted intelligently:
        1. Explicit `version` field in metadata
        2. Filename if versioned (e.g., `0.1.8.md`)
        3. Version pattern in title (e.g., "Bengal 0.1.8")
        4. Full title as fallback
    
    Args:
        source: List of release dicts (from YAML) or Page objects (from section)
        sorted: Sort by version (default: True). Set to False to preserve
                input order for custom sorting.
    
    Returns:
        List of ReleaseView objects, sorted by version (highest first)
    
    Example:
        {% for rel in pages | releases %}
          {{ rel.version }}  {# 0.1.10, 0.1.9, 0.1.8, ... #}
        {% end %}
        
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
