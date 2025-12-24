"""
Section context wrapper for templates.

Provides safe access to Section objects with sensible defaults.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.rendering.context.data_wrappers import ParamsContext

if TYPE_CHECKING:
    from bengal.core.section import Section


class SectionContext:
    """
    Smart wrapper for Section with safe access.

    Returns empty values when no section exists (for non-section pages).
    Template authors can always write {{ section.title }} without checks.

    Example:
        {{ section.title }}
        {{ section.name }}
        {{ section.href }}
        {% for page in section.pages %}
    """

    __slots__ = ("_section", "_params_cache")

    def __init__(self, section: Section | None):
        self._section = section
        self._params_cache: ParamsContext | None = None

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return object.__getattribute__(self, name)

        if self._section is None:
            # Return safe defaults for missing section
            if name in ("pages", "subsections", "children"):
                return []
            if name == "metadata":
                return {}
            return ""

        return getattr(self._section, name, "")

    @property
    def title(self) -> str:
        if self._section:
            return getattr(self._section, "title", "") or ""
        return ""

    @property
    def name(self) -> str:
        if self._section:
            return getattr(self._section, "name", "") or ""
        return ""

    @property
    def path(self) -> str:
        if self._section:
            return str(getattr(self._section, "path", "") or "")
        return ""

    @property
    def href(self) -> str:
        """Section URL path."""
        if self._section:
            # Try _path first (standard section attribute), then url
            url = getattr(self._section, "_path", None) or getattr(self._section, "url", None)
            return str(url) if url else ""
        return ""

    @property
    def pages(self) -> list:
        if self._section:
            return getattr(self._section, "pages", []) or []
        return []

    @property
    def subsections(self) -> list:
        if self._section:
            return getattr(self._section, "subsections", []) or []
        return []

    @property
    def params(self) -> ParamsContext:
        """Section metadata as ParamsContext for safe access (cached)."""
        if self._params_cache is None:
            if self._section and hasattr(self._section, "metadata"):
                self._params_cache = ParamsContext(self._section.metadata)
            else:
                self._params_cache = ParamsContext({})
        return self._params_cache

    @property
    def metadata(self) -> dict[str, Any]:
        """Raw section metadata dict."""
        if self._section and hasattr(self._section, "metadata"):
            return self._section.metadata or {}
        return {}

    def __bool__(self) -> bool:
        """Returns True if a real section exists."""
        return self._section is not None

    def __repr__(self) -> str:
        if self._section:
            return f"SectionContext({self._section.name!r})"
        return "SectionContext(None)"
