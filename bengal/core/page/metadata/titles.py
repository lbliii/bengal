"""
Page metadata titles mixin - title, nav_title, weight, date, version, slug.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.core.utils.shared import resolve_nav_title, sortable_weight

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.page.page_core import PageCore


class PageMetadataTitlesMixin:
    """Title, nav_title, weight, date, version, slug from metadata."""

    source_path: Path
    metadata: Mapping[str, Any]
    core: PageCore | None

    @property
    def title(self) -> str:
        """Get page title from metadata or generate intelligently from context.

        Cost: O(1) cached — CascadeView dict lookup after first metadata access.

        For index pages (_index.md or index.md) without explicit titles,
        uses the parent directory name humanized instead of showing "Index"
        which is not user-friendly in menus, navigation, or page titles.
        """
        meta = self.metadata
        if "title" in meta:
            return str(meta["title"])

        if self.source_path.stem in ("_index", "index"):
            dir_name = self.source_path.parent.name
            return dir_name.replace("-", " ").replace("_", " ").title()

        return self.source_path.stem.replace("-", " ").title()

    @property
    def nav_title(self) -> str:
        """Get navigation title (shorter title for menus/sidebar).

        Cost: O(1) cached — core field or CascadeView lookup + resolve_nav_title.
        """
        nav = (
            self.core.nav_title
            if self.core is not None and self.core.nav_title
            else self.metadata.get("nav_title")
        )
        return resolve_nav_title(str(nav) if nav is not None else None, self.title)

    @property
    def weight(self) -> float:
        """Get page weight for sorting (always returns sortable value).

        Cost: O(1) cached — core field or CascadeView lookup + sortable_weight.
        """
        w = (
            self.core.weight
            if self.core is not None and self.core.weight is not None
            else self.metadata.get("weight")
        )
        return sortable_weight(w)

    @property
    def date(self) -> datetime | None:
        """Get page date from metadata.

        Cost: O(1) cached — CascadeView lookup + parse_date.
        """
        from bengal.utils.primitives.dates import parse_date

        date_value = self.metadata.get("date")
        return parse_date(date_value)

    @property
    def version(self) -> str | None:
        """Get version ID for this page (e.g., 'v3', 'v2').

        Cost: O(1) cached — core field or CascadeView lookup.
        """
        if self.core is not None and self.core.version:
            return self.core.version
        if "_version" in self.metadata:
            return self.metadata.get("_version")
        return self.metadata.get("version")

    @property
    def slug(self) -> str:
        """Get URL slug for the page.

        Cost: O(1) cached — CascadeView lookup or filename stem.
        """
        if "slug" in self.metadata:
            return str(self.metadata["slug"])
        if self.source_path.stem == "_index":
            return self.source_path.parent.name
        return self.source_path.stem
