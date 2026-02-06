"""
Snapshot utilities - shared helpers for the snapshots package.

Extracts common patterns to reduce duplication:
- Content hashing
- Frozen dataclass updates
- Template name resolution
- Progress tracking
- Path indexing

"""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import fields
from pathlib import Path
from typing import Any, Protocol

from bengal.protocols import PageLike

# Re-export PageLike for backwards compatibility
__all__ = ["PageLike"]


# =============================================================================
# Protocols
# =============================================================================


class ProgressManagerProtocol(Protocol):
    """Protocol for progress manager compatibility."""

    def update_phase(
        self, phase: str, *, current: int | None = None, current_item: str | None = None
    ) -> None:
        """Update phase progress."""
        ...


class SiteProtocol(Protocol):
    """Minimal site protocol for utilities."""

    output_dir: Path




# =============================================================================
# Content Hashing
# =============================================================================


def compute_content_hash(content: str) -> str:
    """
    Compute SHA256 hash of content string.

    Used for incremental build change detection.
    """
    return hashlib.sha256(content.encode()).hexdigest()


def compute_page_hash(page: PageLike) -> str:
    """
    Compute content hash from Page object.

    Extracts content from page and computes hash.
    """
    content = getattr(page, "content", "") or ""
    return compute_content_hash(content)


# =============================================================================
# Frozen Dataclass Updates
# =============================================================================


def update_frozen[T](instance: T, **updates: Any) -> T:
    """
    Create new instance of frozen dataclass with updated fields.

    Replaces manual field-by-field copying throughout builder.py.
    Works with any frozen dataclass that has slots.

    Args:
        instance: The frozen dataclass instance to "update"
        **updates: Field names and new values to change

    Returns:
        New instance with updated fields

    Example:
        updated = update_frozen(page_snapshot, section=new_section)
        updated = update_frozen(section_snapshot, root=root_ref, subsections=new_subs)
    """
    cls = type(instance)
    current = {f.name: getattr(instance, f.name) for f in fields(cls)}
    current.update(updates)
    return cls(**current)


# =============================================================================
# Template Name Resolution
# =============================================================================


def resolve_template_name(page: PageLike, default: str = "page.html") -> str:
    """
    Determine template name for a page.

    Checks in order: template, layout, type metadata.

    Args:
        page: Page object to get template for
        default: Default template name if none found

    Returns:
        Template name string
    """
    template = page.metadata.get("template") or page.metadata.get("layout")
    if template:
        return str(template)

    page_type = getattr(page, "type", None) or page.metadata.get("type")
    if page_type:
        return str(page_type)

    return default


# =============================================================================
# Progress Tracking
# =============================================================================


class RenderProgressTracker:
    """
    Thread-safe progress tracking with throttling.

    Consolidates duplicated progress logic from scheduler.py.
    Updates are throttled to avoid overwhelming the UI.

    Example:
        tracker = RenderProgressTracker(progress_manager, site)
        for page in pages:
            render(page)
            tracker.increment(page)
        tracker.finalize(total_pages)
    """

    __slots__ = (
        "_batch_size",
        "_count",
        "_interval",
        "_last_update",
        "_lock",
        "_manager",
        "_site",
    )

    def __init__(
        self,
        manager: ProgressManagerProtocol | None,
        site: SiteProtocol,
        interval: float = 0.1,
        batch_size: int = 10,
    ) -> None:
        """
        Initialize progress tracker.

        Args:
            manager: Progress manager to send updates to (or None)
            site: Site object for path resolution
            interval: Minimum seconds between updates
            batch_size: Update every N items regardless of interval
        """
        self._manager = manager
        self._site = site
        self._interval = interval
        self._batch_size = batch_size
        self._count = 0
        self._lock = threading.Lock()
        self._last_update = 0.0

    @property
    def count(self) -> int:
        """Current count of processed items."""
        return self._count

    def increment(self, page: PageLike) -> int:
        """
        Increment counter and update progress if interval elapsed.

        Thread-safe. Updates are throttled based on interval and batch_size.

        Args:
            page: The page that was just processed

        Returns:
            Current count after increment
        """
        with self._lock:
            self._count += 1
            current = self._count

        if not self._manager:
            return current

        now = time.time()
        should_update = (
            current % self._batch_size == 0 or (now - self._last_update) >= self._interval
        )

        if should_update:
            current_item = self._get_item_name(page)
            self._manager.update_phase(
                "rendering",
                current=current,
                current_item=current_item,
            )
            self._last_update = now

        return current

    def _get_item_name(self, page: PageLike) -> str:
        """Get display name for current item."""
        if page.output_path:
            try:
                return str(page.output_path.relative_to(self._site.output_dir))
            except ValueError:
                pass
        return page.source_path.name

    def finalize(self, total: int) -> None:
        """
        Send final 100% update.

        Args:
            total: Total number of items processed
        """
        if self._manager:
            self._manager.update_phase("rendering", current=total, current_item="")


# =============================================================================
# Path Indexing
# =============================================================================


def build_path_index[T](items: list[T], path_attr: str = "source_path") -> dict[Path, T]:
    """
    Build mapping from path attribute to item.

    Useful for O(1) lookups by path instead of O(n) list scans.

    Args:
        items: List of objects with path attribute
        path_attr: Name of the path attribute

    Returns:
        Dictionary mapping Path to item

    Example:
        page_by_path = build_path_index(site.pages)
        snapshot_by_path = build_path_index(snapshot.pages)
    """
    return {getattr(item, path_attr): item for item in items}


def build_pages_by_template[T](
    pages: list[T],
    template_resolver: Any = None,
) -> dict[str, list[T]]:
    """
    Group pages by template name.

    Args:
        pages: List of page objects
        template_resolver: Optional callable(page) -> str for template name.
                          If None, uses resolve_template_name.

    Returns:
        Dictionary mapping template name to list of pages
    """
    groups: dict[str, list[T]] = {}

    for page in pages:
        if template_resolver:
            template_name = template_resolver(page)
        else:
            template_name = resolve_template_name(page)  # type: ignore[arg-type]

        if template_name not in groups:
            groups[template_name] = []
        groups[template_name].append(page)

    return groups
