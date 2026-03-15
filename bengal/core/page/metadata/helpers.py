"""
Page metadata helpers mixin - visibility, edition, get_user_metadata, etc.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any


class PageMetadataHelpersMixin:
    """Visibility flags, edition/variant, get_user_metadata, assigned_template."""

    metadata: object

    @property
    def hidden(self) -> bool:
        """Check if page is hidden (unlisted)."""
        return bool(self.metadata.get("hidden", False))

    @cached_property
    def edition(self) -> tuple[str, ...]:
        """Get edition/variant list from frontmatter for multi-variant builds."""
        val = self.metadata.get("edition")
        if val is None:
            return ()
        if isinstance(val, str):
            return (val,) if val else ()
        if isinstance(val, list):
            return tuple(str(v).strip() for v in val if v is not None and str(v).strip())
        return ()

    def in_variant(self, variant: str | None) -> bool:
        """
        Check if page should be included when building for the given variant.

        When params.edition is set, pages are excluded if their edition list
        does not include that value. Pages with no edition are included in all.
        """
        if variant is None or not str(variant).strip():
            return True
        editions = self.edition
        if not editions:
            return True
        return variant in editions

    def get_user_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get user-defined frontmatter value.

        Does NOT return internal keys (prefixed with `_`).
        """
        if key.startswith("_"):
            return default
        return self.metadata.get(key, default)

    def get_internal_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get internal metadata value.

        Only returns keys prefixed with `_`.
        Auto-prefixes key if not already prefixed.
        """
        if not key.startswith("_"):
            key = f"_{key}"
        return self.metadata.get(key, default)

    @property
    def assigned_template(self) -> str | None:
        """Template explicitly assigned to this page via frontmatter."""
        val = self.metadata.get("template")
        return str(val) if val is not None else None

    @property
    def content_type_name(self) -> str | None:
        """Content type assigned to this page."""
        val = self.metadata.get("content_type")
        return str(val) if val is not None else None
