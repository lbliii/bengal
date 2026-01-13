"""
Template context wrappers for ergonomic URL handling.

Wraps Page and Section objects so that .href automatically includes baseurl
in templates, making it impossible to forget baseurl in href/src attributes.
Provides transparent delegation to wrapped objects while adding baseurl handling.

Key Concepts:
- Auto-baseurl: Automatically applies baseurl to .href property
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

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site


class TemplatePageWrapper:
    """
    Wraps Page objects to auto-apply baseurl to .href in templates.
    
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
        wrapped.href  # Returns "/bengal/docs/page/" (with baseurl)
        wrapped.title  # Delegates to page.title
        
    """

    def __init__(self, page: Page, baseurl: str = ""):
        """
        Initialize wrapper.

        Args:
            page: Page object to wrap
            baseurl: Base URL from site config (can be empty, path-only, or absolute)
        """
        self._page: Page = page
        self._baseurl = (baseurl or "").rstrip("/")

    @property
    def href(self) -> str:
        """
        URL with baseurl applied (for templates).

        This is the property templates should use for href/src attributes.
        It automatically includes baseurl, so theme developers don't need
        to remember to use permalink or filters.
        """
        # Get site-relative path from wrapped page (without baseurl)
        rel = self._page._path

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
    Wraps Section objects to auto-apply baseurl to .href in templates.
    
    Provides transparent wrapper that automatically applies baseurl to section URLs,
    similar to TemplatePageWrapper. Also wraps pages and subsections when accessed
    to ensure consistent baseurl handling throughout the section hierarchy.
    
    Creation:
        Direct instantiation: TemplateSectionWrapper(section, baseurl="")
            - Created by TemplateEngine for template context
            - Requires Section instance and optional baseurl
    
    Attributes:
        _section: Wrapped Section object
        _baseurl: Base URL from site config
    
    Relationships:
        - Uses: Section for wrapped section object
        - Used by: TemplateEngine for template context
        - Used in: Templates via template context
        - Wraps: Pages and subsections when accessed
    
    Examples:
        wrapped = TemplateSectionWrapper(section, baseurl="/bengal")
        wrapped.href  # Returns "/bengal/docs/section/" (with baseurl)
        wrapped.pages  # Returns wrapped pages with baseurl
        
    """

    def __init__(self, section: Section, baseurl: str = ""):
        """
        Initialize wrapper.

        Args:
            section: Section object to wrap
            baseurl: Base URL from site config
        """
        self._section: Section = section
        self._baseurl = (baseurl or "").rstrip("/")

    @property
    def href(self) -> str:
        """URL with baseurl applied (for templates)."""
        rel = self._section._path

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
    def pages(self) -> list[TemplatePageWrapper]:
        """Return wrapped pages."""
        if not hasattr(self._section, "pages"):
            return []
        return [wrap_for_template(p, self._baseurl) for p in self._section.pages]

    @property
    def subsections(self) -> list[TemplateSectionWrapper]:
        """Return wrapped subsections."""
        if not hasattr(self._section, "subsections"):
            return []
        return [wrap_for_template(s, self._baseurl) for s in self._section.subsections]

    @property
    def sorted_pages(self) -> list[TemplatePageWrapper]:
        """Return wrapped sorted pages."""
        if not hasattr(self._section, "sorted_pages"):
            return []
        return [wrap_for_template(p, self._baseurl) for p in self._section.sorted_pages]

    @property
    def sorted_subsections(self) -> list[TemplateSectionWrapper]:
        """Return wrapped sorted subsections."""
        if not hasattr(self._section, "sorted_subsections"):
            return []
        return [wrap_for_template(s, self._baseurl) for s in self._section.sorted_subsections]

    @property
    def index_page(self) -> TemplatePageWrapper | None:
        """Return wrapped index page."""
        if not hasattr(self._section, "index_page") or self._section.index_page is None:
            return None
        wrapped = wrap_for_template(self._section.index_page, self._baseurl)
        return wrapped if isinstance(wrapped, TemplatePageWrapper) else None

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
    are automatically wrapped so they have .href with baseurl applied.
    
    PERF: Wrapped lists are cached to avoid O(n) list creation on every access.
    Cache is keyed by the underlying list length, so it auto-invalidates when
    pages/sections are added/removed (e.g., during dev server rebuilds).
        
    """

    __slots__ = (
        "_site",
        "_baseurl",
        "_pages_cache",
        "_pages_cache_len",
        "_sections_cache",
        "_sections_cache_len",
        "_regular_pages_cache",
        "_regular_pages_cache_len",
    )

    def __init__(self, site: Site, baseurl: str = ""):
        """
        Initialize wrapper.

        Args:
            site: Site object to wrap
            baseurl: Base URL from site config
        """
        self._site: Site = site
        self._baseurl = baseurl
        # PERF: Caches for wrapped lists (avoids O(n) list creation on each access)
        self._pages_cache: list[TemplatePageWrapper] | None = None
        self._pages_cache_len: int = -1
        self._sections_cache: list[TemplateSectionWrapper] | None = None
        self._sections_cache_len: int = -1
        self._regular_pages_cache: list[TemplatePageWrapper] | None = None
        self._regular_pages_cache_len: int = -1

    @property
    def pages(self) -> list[TemplatePageWrapper]:
        """Return wrapped pages (cached)."""
        current_len = len(self._site.pages)
        if self._pages_cache is None or self._pages_cache_len != current_len:
            self._pages_cache = [wrap_for_template(p, self._baseurl) for p in self._site.pages]
            self._pages_cache_len = current_len
        return self._pages_cache

    @property
    def sections(self) -> list[TemplateSectionWrapper]:
        """Return wrapped sections (cached)."""
        current_len = len(self._site.sections)
        if self._sections_cache is None or self._sections_cache_len != current_len:
            self._sections_cache = [
                wrap_for_template(s, self._baseurl) for s in self._site.sections
            ]
            self._sections_cache_len = current_len
        return self._sections_cache

    @property
    def regular_pages(self) -> list[TemplatePageWrapper]:
        """Return wrapped regular pages (cached)."""
        current_len = len(self._site.regular_pages)
        if self._regular_pages_cache is None or self._regular_pages_cache_len != current_len:
            self._regular_pages_cache = [
                wrap_for_template(p, self._baseurl) for p in self._site.regular_pages
            ]
            self._regular_pages_cache_len = current_len
        return self._regular_pages_cache

    def __getattr__(self, name: str) -> Any:
        """Delegate all other attributes to wrapped site."""
        return getattr(self._site, name)


def wrap_for_template(
    obj: Page | Section | Site | object | None, baseurl: str = ""
) -> TemplatePageWrapper | TemplateSectionWrapper | TemplateSiteWrapper | object | None:
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

    # Check if it has href or _path attribute (Page, Section, or SimpleNamespace from special pages)
    if hasattr(obj, "href") or hasattr(obj, "_path"):
        # Check if it's a Section (has index_page attribute)
        if hasattr(obj, "index_page"):
            return TemplateSectionWrapper(obj, baseurl)

        # Check if it's a Page-like object (has _path property)
        if hasattr(obj, "_path"):
            return TemplatePageWrapper(obj, baseurl)

        # Check if it's a SimpleNamespace (special pages like 404, search, graph)
        # These might have href or _path, so we create a simple wrapper
        from types import SimpleNamespace

        if isinstance(obj, SimpleNamespace):
            return TemplatePageWrapper(obj, baseurl)

    # Not a Page/Section/SimpleNamespace, return as-is
    return obj
