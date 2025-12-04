"""
Template context wrappers for ergonomic URL handling.

Wraps Page and Section objects so that .url automatically includes baseurl
in templates, making it impossible to forget baseurl in href/src attributes.
Provides transparent delegation to wrapped objects while adding baseurl handling.

Key Concepts:
    - Auto-baseurl: Automatically applies baseurl to .url property
    - Transparent delegation: All other properties delegate to wrapped object
    - Multiple baseurl formats: Supports path, absolute, file, and S3 URLs
    - Template ergonomics: Simplifies template code by removing baseurl handling

Related Modules:
    - bengal.rendering.template_engine: Template engine that uses wrappers
    - bengal.core.page: Page objects being wrapped
    - bengal.core.section: Section objects being wrapped

See Also:
    - bengal/rendering/template_context.py:TemplatePageWrapper for page wrapper
    - bengal/rendering/template_context.py:TemplateSectionWrapper for section wrapper
"""

from __future__ import annotations

from typing import Any


class TemplatePageWrapper:
    """
    Wraps Page objects to auto-apply baseurl to .url in templates.

    Provides transparent wrapper that automatically applies baseurl to page URLs,
    making templates ergonomic. All other page properties delegate to the wrapped
    page object, maintaining full compatibility.

    Creation:
        Direct instantiation: TemplatePageWrapper(page, baseurl="")
            - Created by TemplateEngine for template context
            - Requires Page instance and optional baseurl

    Attributes:
        _page: Wrapped Page object
        _baseurl: Base URL from site config (can be empty, path-only, or absolute)

    Relationships:
        - Uses: Page for wrapped page object
        - Used by: TemplateEngine for template context
        - Used in: Templates via template context

    Baseurl Formats Supported:
        - Path-only: `/bengal` → `/bengal/docs/page/`
        - Absolute: `https://example.com` → `https://example.com/docs/page/`
        - File protocol: `file:///path/to/site` → `file:///path/to/site/docs/page/`
        - S3: `s3://bucket/path` → `s3://bucket/path/docs/page/`

    Examples:
        wrapped = TemplatePageWrapper(page, baseurl="/bengal")
        wrapped.url  # Returns "/bengal/docs/page/" (with baseurl)
        wrapped.title  # Delegates to page.title
        wrapped.permalink  # Still works (returns same as url)
    """

    def __init__(self, page: Any, baseurl: str = ""):
        """
        Initialize wrapper.

        Args:
            page: Page object to wrap
            baseurl: Base URL from site config (can be empty, path-only, or absolute)
        """
        self._page = page
        self._baseurl = (baseurl or "").rstrip("/")

    @property
    def url(self) -> str:
        """
        URL with baseurl applied (for templates).

        This is the property templates should use for href/src attributes.
        It automatically includes baseurl, so theme developers don't need
        to remember to use permalink or filters.
        """
        # Get relative URL from wrapped page
        rel = self._page.url if hasattr(self._page, "url") else "/"

        # Normalize relative URL
        if not rel:
            rel = "/"
        if not rel.startswith("/"):
            rel = "/" + rel

        # If no baseurl, return relative URL as-is
        if not self._baseurl:
            return rel

        # Apply baseurl based on format
        baseurl = self._baseurl.rstrip("/")

        # Absolute URLs (http://, https://, file://, s3://, etc.)
        if baseurl.startswith(("http://", "https://", "file://", "s3://")):
            return f"{baseurl}{rel}"

        # Path-only baseurl (e.g., /bengal)
        base_path = "/" + baseurl.lstrip("/")
        return f"{base_path}{rel}"

    @property
    def permalink(self) -> str:
        """
        Alias for url (for backward compatibility).

        Both url and permalink now return the same value (with baseurl).
        This maintains compatibility with existing templates that use permalink.
        """
        return self.url

    @property
    def relative_url(self) -> str:
        """
        Relative URL without baseurl (for comparisons).

        Use this when you need the relative URL for comparisons or logic.
        For display URLs, use .url (which includes baseurl).
        """
        return self._page.url if hasattr(self._page, "url") else "/"

    def __getattr__(self, name: str) -> Any:
        """
        Delegate all other attributes to wrapped page.

        This makes the wrapper transparent - all page properties work as expected.
        """
        return getattr(self._page, name)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"TemplatePageWrapper(page={self._page!r}, baseurl={self._baseurl!r})"


class TemplateSectionWrapper:
    """
    Wraps Section objects to auto-apply baseurl to .url in templates.

    Same pattern as TemplatePageWrapper but for Section objects.
    Sections also have url/permalink properties that need baseurl.
    Also wraps pages/subsections when accessed so they have .relative_url.
    """

    def __init__(self, section: Any, baseurl: str = ""):
        """
        Initialize wrapper.

        Args:
            section: Section object to wrap
            baseurl: Base URL from site config
        """
        self._section = section
        self._baseurl = (baseurl or "").rstrip("/")

    @property
    def url(self) -> str:
        """URL with baseurl applied (for templates)."""
        rel = self._section.url if hasattr(self._section, "url") else "/"

        if not rel:
            rel = "/"
        if not rel.startswith("/"):
            rel = "/" + rel

        if not self._baseurl:
            return rel

        baseurl = self._baseurl.rstrip("/")

        if baseurl.startswith(("http://", "https://", "file://", "s3://")):
            return f"{baseurl}{rel}"

        base_path = "/" + baseurl.lstrip("/")
        return f"{base_path}{rel}"

    @property
    def permalink(self) -> str:
        """Alias for url (for backward compatibility)."""
        return self.url

    @property
    def relative_url(self) -> str:
        """Relative URL without baseurl (for comparisons)."""
        return self._section.url if hasattr(self._section, "url") else "/"

    @property
    def pages(self) -> list:
        """Return wrapped pages."""
        if not hasattr(self._section, "pages"):
            return []
        return [wrap_for_template(p, self._baseurl) for p in self._section.pages]

    @property
    def subsections(self) -> list:
        """Return wrapped subsections."""
        if not hasattr(self._section, "subsections"):
            return []
        return [wrap_for_template(s, self._baseurl) for s in self._section.subsections]

    @property
    def sorted_pages(self) -> list:
        """Return wrapped sorted pages."""
        if not hasattr(self._section, "sorted_pages"):
            return []
        return [wrap_for_template(p, self._baseurl) for p in self._section.sorted_pages]

    @property
    def sorted_subsections(self) -> list:
        """Return wrapped sorted subsections."""
        if not hasattr(self._section, "sorted_subsections"):
            return []
        return [wrap_for_template(s, self._baseurl) for s in self._section.sorted_subsections]

    @property
    def index_page(self) -> Any:
        """Return wrapped index page."""
        if not hasattr(self._section, "index_page") or self._section.index_page is None:
            return None
        return wrap_for_template(self._section.index_page, self._baseurl)

    def __getattr__(self, name: str) -> Any:
        """Delegate all other attributes to wrapped section."""
        return getattr(self._section, name)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"TemplateSectionWrapper(section={self._section!r}, baseurl={self._baseurl!r})"


class TemplateSiteWrapper:
    """
    Wraps Site object to auto-wrap pages/sections when accessed from templates.

    When templates access site.pages or site.sections, the pages/sections
    are automatically wrapped so they have .relative_url and .url includes baseurl.
    """

    def __init__(self, site: Any, baseurl: str = ""):
        """
        Initialize wrapper.

        Args:
            site: Site object to wrap
            baseurl: Base URL from site config
        """
        self._site = site
        self._baseurl = baseurl

    @property
    def pages(self) -> list:
        """Return wrapped pages."""
        return [wrap_for_template(p, self._baseurl) for p in self._site.pages]

    @property
    def sections(self) -> list:
        """Return wrapped sections."""
        return [wrap_for_template(s, self._baseurl) for s in self._site.sections]

    @property
    def regular_pages(self) -> list:
        """Return wrapped regular pages."""
        return [wrap_for_template(p, self._baseurl) for p in self._site.regular_pages]

    def __getattr__(self, name: str) -> Any:
        """Delegate all other attributes to wrapped site."""
        return getattr(self._site, name)


def wrap_for_template(obj: Any, baseurl: str = "") -> Any:
    """
    Wrap Page or Section objects for template context.

    This function automatically detects the object type and wraps it appropriately.
    Other objects are returned unchanged.

    Args:
        obj: Page, Section, SimpleNamespace (special pages), or other object
        baseurl: Base URL from site config

    Returns:
        Wrapped object (if Page/Section/SimpleNamespace with url) or original object
    """
    # Skip None
    if obj is None:
        return obj

    # Check if it's already wrapped
    if isinstance(obj, (TemplatePageWrapper, TemplateSectionWrapper, TemplateSiteWrapper)):
        return obj

    # Check if it has a url attribute (Page, Section, or SimpleNamespace from special pages)
    if hasattr(obj, "url"):
        # Check if it's a Section (has index_page attribute)
        if hasattr(obj, "index_page"):
            return TemplateSectionWrapper(obj, baseurl)

        # Check if it's a Page-like object (has permalink property)
        if hasattr(obj, "permalink"):
            return TemplatePageWrapper(obj, baseurl)

        # Check if it's a SimpleNamespace (special pages like 404, search, graph)
        # These have url but no permalink, so we create a simple wrapper
        from types import SimpleNamespace

        if isinstance(obj, SimpleNamespace):
            return TemplatePageWrapper(obj, baseurl)

    # Not a Page/Section/SimpleNamespace, return as-is
    return obj
