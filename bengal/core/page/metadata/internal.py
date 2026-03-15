"""
Page metadata internal mixin - build-injected flags and orchestrator data.

Provides is_autodoc, tag_slug, autodoc_template, internal_posts, etc.
These are internal keys (_tag_slug, _posts, etc.) set by orchestrators.
"""

from __future__ import annotations


class PageMetadataInternalMixin:
    """Internal build flags and orchestrator-injected data."""

    metadata: object
    _raw_metadata: object

    def _raw_get(self, key: str, default: object = None) -> object:
        """Get from _raw_metadata first, fallback to metadata."""
        raw = getattr(self, "_raw_metadata", None)
        if raw is not None and hasattr(raw, "get"):
            val = raw.get(key)
            if val is not None:
                return val
        return self.metadata.get(key, default)

    @property
    def is_autodoc(self) -> bool:
        """Whether this is an autodoc-generated API page."""
        return bool(self._raw_get("is_autodoc"))

    @property
    def tag_slug(self) -> str | None:
        """Tag slug for generated tag pages."""
        return self._raw_get("_tag_slug")

    @property
    def autodoc_template(self) -> str | None:
        """Autodoc template override for auto-generated API doc pages."""
        return self._raw_get("_autodoc_template")

    @property
    def tag_name(self) -> str | None:
        """Display name for generated tag pages (e.g., "Python")."""
        return self._raw_get("_tag")

    @property
    def taxonomy_term(self) -> str | None:
        """Taxonomy term slug for provenance tracking on generated tag pages."""
        return self._raw_get("_taxonomy_term")

    @property
    def internal_posts(self) -> list:
        """Posts list injected by section/taxonomy orchestrators for generated pages."""
        val = self._raw_get("_posts", [])
        return val if isinstance(val, list) else []

    @property
    def internal_section(self):
        """Section object injected by SectionOrchestrator for section index pages."""
        return self._raw_get("_section")

    @property
    def internal_subsections(self) -> list:
        """Subsections list injected by SectionOrchestrator."""
        val = self._raw_get("_subsections", [])
        return val if isinstance(val, list) else []

    @property
    def internal_paginator(self):
        """Paginator object for paginated section/tag pages."""
        return self._raw_get("_paginator")

    @property
    def internal_page_num(self) -> int:
        """Page number for paginated pages (1-indexed)."""
        val = self._raw_get("_page_num", 1)
        return int(val) if val is not None else 1

    @property
    def internal_tags_index(self) -> dict:
        """Tags index dict for the tag index page (maps slug -> tag data)."""
        val = self._raw_get("_tags", {})
        return val if isinstance(val, dict) else {}
