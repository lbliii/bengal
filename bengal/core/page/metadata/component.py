"""
Page metadata component mixin - type, variant, props, draft, keywords.
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.page.page_core import PageCore


class PageMetadataComponentMixin:
    """Component Model: type, variant, props, draft, keywords."""

    metadata: object
    core: PageCore | None

    @property
    def type(self) -> str | None:
        """Get page type from metadata (frontmatter or cascade, already merged)."""
        val = self.metadata.get("type")
        return str(val) if val is not None else None

    @property
    def description(self) -> str:
        """Get page description from core metadata (preferred) or frontmatter."""
        if self.core is not None and self.core.description:
            return self.core.description
        return str(self.metadata.get("description", ""))

    @property
    def variant(self) -> str | None:
        """Get visual variant from metadata (frontmatter or cascade, already merged)."""
        return (
            self.metadata.get("variant")
            or self.metadata.get("layout")
            or self.metadata.get("hero_style")
        )

    @property
    def props(self) -> dict[str, Any]:
        """Get page props (alias for metadata). Component Model: Data."""
        return self.metadata

    @property
    def params(self) -> dict[str, Any]:
        """Get page params (alias for metadata)."""
        return self.metadata

    @property
    def draft(self) -> bool:
        """Check if page is marked as draft."""
        return bool(self.metadata.get("draft", False))

    @cached_property
    def keywords(self) -> tuple[str, ...]:
        """Get page keywords from metadata."""
        keywords = self.metadata.get("keywords", [])
        if isinstance(keywords, str):
            return tuple(k.strip() for k in keywords.split(",") if k.strip())
        if isinstance(keywords, list):
            return tuple(s for s in (str(k).strip() for k in keywords if k is not None) if s)
        return ()
