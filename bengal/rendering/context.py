"""
Unified template context system for Bengal SSG.

Provides smart context objects that enable ergonomic template development:
- Safe dot-notation access (no .get() needed)
- Sensible defaults for missing values
- Consistent API across all page types
- No UndefinedError exceptions

Design Philosophy:
    Template developers should write declarative, beautiful templates without
    defensive coding. Every access should "just work" with intuitive fallbacks.

Context Layers:
    Layer 1 - Globals (always available):
        site, config, theme, menus, bengal

    Layer 2 - Page Context (per render):
        page, params, section, content, toc, toc_items
        meta_desc, reading_time, excerpt

    Layer 3 - Specialized (page-type specific):
        posts, pages, subsections (section indexes)
        tag, tags (tag pages)
        element (autodoc pages)

Usage in Templates:
    {{ site.title }}           # Site title (never undefined)
    {{ theme.hero_style }}     # Theme config (defaults to '')
    {{ params.author }}        # Page frontmatter (defaults to '')
    {{ section.title }}        # Section title ('' if no section)

    {% if theme.has('navigation.toc') %}
    {% if page is draft %}

Example:
    from bengal.rendering.context import build_page_context

    context = build_page_context(page, site, content=html)
    rendered = template.render(**context)
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from markupsafe import Markup

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site
    from bengal.core.theme import Theme


class SmartDict:
    """
    A dict wrapper that allows safe dot-notation access.

    Returns empty string for missing string keys, empty list for missing
    list keys, and empty dict for missing dict keys. Enables template
    developers to write clean code without defensive checks.

    Example:
        >>> d = SmartDict({'name': 'Bengal'})
        >>> d.name
        'Bengal'
        >>> d.missing_key
        ''
        >>> d.get('missing', 'default')
        'default'
    """

    def __init__(self, data: dict[str, Any] | None = None):
        self._data = data or {}

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        return self._data.get(name, "")

    def __getitem__(self, key: str) -> Any:
        return self._data.get(key, "")

    def get(self, key: str, default: Any = "") -> Any:
        """Get with explicit default."""
        return self._data.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __bool__(self) -> bool:
        return bool(self._data)

    def __repr__(self) -> str:
        return f"SmartDict({self._data!r})"

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()


class SiteContext:
    """
    Smart wrapper for Site object with ergonomic access patterns.

    Provides clean access to site configuration with sensible defaults.
    All properties return safe values (never None for strings).

    Example:
        {{ site.title }}             # Site title
        {{ site.logo }}              # Logo URL ('' if not set)
        {{ site.baseurl }}           # Base URL ('' if not set)
        {{ site.author }}            # Default author
        {{ site.params.repo_url }}   # Custom params
    """

    __slots__ = ("_site",)

    def __init__(self, site: Site):
        self._site = site

    def __getattr__(self, name: str) -> Any:
        """Proxy to underlying site, with safe fallbacks."""
        # For wrapper's own underscore attrs, use normal attribute access
        if name == "_site":
            return object.__getattribute__(self, "_site")

        # Check for property on site first (including underscore attrs like _dev_menu_metadata)
        if hasattr(self._site, name):
            return getattr(self._site, name)

        # Fall back to config lookup for non-underscore names
        if not name.startswith("_"):
            return self._site.config.get(name, "")

        # Return None for missing underscore attrs (safer than raising)
        return None

    @property
    def title(self) -> str:
        return self._site.config.get("title", "") or ""

    @property
    def description(self) -> str:
        return self._site.config.get("description", "") or ""

    @property
    def baseurl(self) -> str:
        return self._site.config.get("baseurl", "") or ""

    @property
    def author(self) -> str:
        return self._site.config.get("author", "") or ""

    @property
    def logo(self) -> str:
        """Get logo image URL from various config locations."""
        cfg = self._site.config
        return cfg.get("logo_image", "") or cfg.get("site", {}).get("logo_image", "") or ""

    @property
    def logo_text(self) -> str:
        """Get logo text from various config locations."""
        cfg = self._site.config
        return cfg.get("logo_text", "") or cfg.get("site", {}).get("logo_text", "") or ""

    @property
    def params(self) -> ParamsContext:
        """
        Site-level custom parameters from [params] config section.

        Returns a ParamsContext for safe nested access.

        Example:
            {{ site.params.repo_url }}
            {{ site.params.social.twitter }}
        """
        return ParamsContext(self._site.config.get("params", {}))

    def __bool__(self) -> bool:
        """Always truthy since site always exists."""
        return True

    def __repr__(self) -> str:
        return f"SiteContext({self.title!r})"


class ThemeContext:
    """
    Smart wrapper for Theme configuration with ergonomic access.

    Provides clean access to theme settings:
    - Direct properties: name, appearance, palette, features
    - Custom config via get() or dot notation
    - Feature checking via has()

    Example:
        {{ theme.name }}                    # Theme name
        {{ theme.appearance }}              # 'light', 'dark', or 'system'
        {{ theme.hero_style }}              # Custom config value
        {% if theme.has('navigation.toc') %}
        {% if 'feature' in theme.features %}
    """

    __slots__ = ("_theme",)

    def __init__(self, theme: Theme | None):
        self._theme = theme

    @classmethod
    def _empty(cls) -> ThemeContext:
        """Create an empty ThemeContext for when no theme is configured."""
        return cls(None)

    def __getattr__(self, name: str) -> Any:
        """Access theme properties or config values."""
        if name.startswith("_"):
            return object.__getattribute__(self, name)

        if self._theme is None:
            return ""

        # Check for direct property on Theme first
        if hasattr(self._theme, name) and not name.startswith("_"):
            val = getattr(self._theme, name)
            if val is not None:
                return val

        # Fall back to theme.config
        if self._theme.config:
            return self._theme.config.get(name, "")
        return ""

    @property
    def name(self) -> str:
        if self._theme is None:
            return "default"
        return self._theme.name or "default"

    @property
    def appearance(self) -> str:
        """Default appearance mode (light/dark/system)."""
        if self._theme is None:
            return "system"
        return self._theme.default_appearance or "system"

    @property
    def palette(self) -> str:
        """Default color palette."""
        if self._theme is None:
            return ""
        return self._theme.default_palette or ""

    @property
    def features(self) -> list[str]:
        """List of enabled feature flags."""
        if self._theme is None:
            return []
        return self._theme.features or []

    @property
    def config(self) -> ParamsContext:
        """Theme config as ParamsContext for safe nested access."""
        if self._theme is None or self._theme.config is None:
            return ParamsContext({})
        return ParamsContext(self._theme.config)

    def has(self, feature: str) -> bool:
        """
        Check if a feature is enabled.

        Example:
            {% if theme.has('navigation.toc') %}
        """
        if self._theme is None:
            return False
        return feature in (self._theme.features or [])

    def get(self, key: str, default: Any = "") -> Any:
        """
        Get custom theme config value with default.

        Example:
            {{ theme.get('hero_style', 'editorial') }}
        """
        if self._theme is None:
            return default
        if self._theme.config:
            return self._theme.config.get(key, default)
        return default

    def __bool__(self) -> bool:
        """Returns True if a real theme exists."""
        return self._theme is not None


class ConfigContext:
    """
    Smart wrapper for site configuration with safe access.

    Allows both dot notation and get() access to config values.
    Never raises KeyError or returns None for string values.

    Example:
        {{ config.title }}
        {{ config.get('baseurl', '/') }}
        {{ config.params.repo_url }}
    """

    __slots__ = ("_config",)

    def __init__(self, config: dict[str, Any]):
        self._config = config or {}

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return object.__getattribute__(self, name)

        value = self._config.get(name)

        # Wrap nested dicts in SmartDict for chained access
        if isinstance(value, dict):
            return SmartDict(value)

        return value if value is not None else ""

    def __getitem__(self, key: str) -> Any:
        return self.__getattr__(key)

    def get(self, key: str, default: Any = "") -> Any:
        """Get with explicit default."""
        value = self._config.get(key)
        if value is None:
            return default
        if isinstance(value, dict):
            return SmartDict(value)
        return value

    def __contains__(self, key: str) -> bool:
        return key in self._config


class ParamsContext:
    """
    Smart wrapper for page metadata/frontmatter with recursive nesting support.

    Provides clean access to page params without .get() everywhere.
    Nested dicts are recursively wrapped for safe chained access.

    Example:
        {{ params.author }}
        {{ params.description }}
        {{ params.social.twitter.handle }}  # Deep access is safe
        {{ params.get('custom_field', 'default') }}

        {% for key, value in params.items() %}

    Performance:
        Nested dictionaries are wrapped lazily and cached on first access.
        This prevents repeatedly creating new ParamsContext objects for the same
        nested data, which is especially important for deeply nested structures
        or when accessed in template loops.
    """

    __slots__ = ("_data", "_cache")

    def __init__(self, metadata: dict[str, Any] | None):
        object.__setattr__(self, "_data", metadata or {})
        object.__setattr__(self, "_cache", {})

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return object.__getattribute__(self, name)

        # Check cache first for wrapped nested dicts
        cache = object.__getattribute__(self, "_cache")
        if name in cache:
            return cache[name]

        data = object.__getattribute__(self, "_data")
        value = data.get(name)

        # Recursively wrap nested dicts for chained access (with caching)
        if isinstance(value, dict):
            wrapped = ParamsContext(value)
            cache[name] = wrapped
            return wrapped

        # Return empty string for missing/None, preserving other falsy values
        if value is None:
            return ""
        return value

    def __getitem__(self, key: str) -> Any:
        return self.__getattr__(key)

    def get(self, key: str, default: Any = "") -> Any:
        """Get with explicit default."""
        value = self._data.get(key)
        if value is None:
            return default
        if isinstance(value, dict):
            return ParamsContext(value)
        return value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __bool__(self) -> bool:
        return bool(self._data)

    def __iter__(self):
        """Iterate over keys."""
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def keys(self):
        """Return keys view."""
        return self._data.keys()

    def values(self):
        """Return values view."""
        return self._data.values()

    def items(self):
        """Return items view."""
        return self._data.items()

    def __repr__(self) -> str:
        return f"ParamsContext({self._data!r})"


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

    __slots__ = ("_section",)

    def __init__(self, section: Section | None):
        self._section = section

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
        """Section metadata as ParamsContext for safe access."""
        if self._section and hasattr(self._section, "metadata"):
            return ParamsContext(self._section.metadata)
        return ParamsContext({})

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


class CascadingParamsContext:
    """
    Params with inheritance: page → section → site.

    Access {{ params.author }} and get the most specific value defined.
    Implements Eleventy-style data cascade for template variables.

    Cascade order (most to least specific):
        1. Page frontmatter
        2. Section _index.md frontmatter
        3. Site bengal.toml [params]

    Example:
        # bengal.toml
        # [params]
        # company = "Acme Corp"

        # blog/_index.md
        # ---
        # params:
        #   author: Blog Team
        # ---

        # blog/post.md
        # ---
        # author: Jane Doe
        # ---

        {{ params.author }}   → "Jane Doe" (page)
        {{ params.company }}  → "Acme Corp" (cascaded from site)

    Performance:
        Nested dictionaries are wrapped lazily and cached on first access.
    """

    __slots__ = ("_page", "_section", "_site", "_cache")

    def __init__(
        self,
        page_params: dict[str, Any] | None = None,
        section_params: dict[str, Any] | None = None,
        site_params: dict[str, Any] | None = None,
    ):
        object.__setattr__(self, "_page", page_params or {})
        object.__setattr__(self, "_section", section_params or {})
        object.__setattr__(self, "_site", site_params or {})
        object.__setattr__(self, "_cache", {})

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return object.__getattribute__(self, name)

        # Check cache first for wrapped nested dicts
        cache = object.__getattribute__(self, "_cache")
        if name in cache:
            return cache[name]

        page = object.__getattribute__(self, "_page")
        section = object.__getattribute__(self, "_section")
        site = object.__getattribute__(self, "_site")

        # Check page first (most specific)
        if name in page:
            value = page[name]
            if isinstance(value, dict):
                wrapped = CascadingParamsContext(
                    value,
                    section.get(name, {}) if isinstance(section.get(name), dict) else {},
                    site.get(name, {}) if isinstance(site.get(name), dict) else {},
                )
                cache[name] = wrapped
                return wrapped
            return value if value is not None else ""

        # Then section
        if name in section:
            value = section[name]
            if isinstance(value, dict):
                wrapped = CascadingParamsContext(
                    {},
                    value,
                    site.get(name, {}) if isinstance(site.get(name), dict) else {},
                )
                cache[name] = wrapped
                return wrapped
            return value if value is not None else ""

        # Finally site
        if name in site:
            value = site[name]
            if isinstance(value, dict):
                wrapped = CascadingParamsContext({}, {}, value)
                cache[name] = wrapped
                return wrapped
            return value if value is not None else ""

        # Not found anywhere
        return ""

    def __getitem__(self, key: str) -> Any:
        return self.__getattr__(key)

    def get(self, key: str, default: Any = "") -> Any:
        """Get with explicit default, checking cascade."""
        page = object.__getattribute__(self, "_page")
        section = object.__getattribute__(self, "_section")
        site = object.__getattribute__(self, "_site")

        # Check page first
        if key in page:
            value = page[key]
            return value if value is not None else default
        # Then section
        if key in section:
            value = section[key]
            return value if value is not None else default
        # Finally site
        if key in site:
            value = site[key]
            return value if value is not None else default
        return default

    def __contains__(self, key: str) -> bool:
        page = object.__getattribute__(self, "_page")
        section = object.__getattribute__(self, "_section")
        site = object.__getattribute__(self, "_site")
        return key in page or key in section or key in site

    def __bool__(self) -> bool:
        page = object.__getattribute__(self, "_page")
        section = object.__getattribute__(self, "_section")
        site = object.__getattribute__(self, "_site")
        return bool(page) or bool(section) or bool(site)

    def __iter__(self):
        """Iterate over all keys from all levels."""
        page = object.__getattribute__(self, "_page")
        section = object.__getattribute__(self, "_section")
        site = object.__getattribute__(self, "_site")

        seen = set()
        for key in page:
            if key not in seen:
                seen.add(key)
                yield key
        for key in section:
            if key not in seen:
                seen.add(key)
                yield key
        for key in site:
            if key not in seen:
                seen.add(key)
                yield key

    def keys(self):
        """Return all keys from all cascade levels."""
        page = object.__getattribute__(self, "_page")
        section = object.__getattribute__(self, "_section")
        site = object.__getattribute__(self, "_site")
        return set(page.keys()) | set(section.keys()) | set(site.keys())

    def items(self):
        """Return items with cascade resolution."""
        page = object.__getattribute__(self, "_page")
        section = object.__getattribute__(self, "_section")
        site = object.__getattribute__(self, "_site")

        result = {}
        # Start with site (least specific)
        result.update(site)
        # Override with section
        result.update(section)
        # Override with page (most specific)
        result.update(page)
        return result.items()

    def __repr__(self) -> str:
        page = object.__getattribute__(self, "_page")
        section = object.__getattribute__(self, "_section")
        site = object.__getattribute__(self, "_site")
        return f"CascadingParamsContext(page={page!r}, section={section!r}, site={site!r})"


class MenusContext:
    """
    Smart access to navigation menus.

    Example:
        {% for item in menus.main %}
        {% for item in menus.footer %}
        {% for item in menus.get('sidebar') %}
    """

    __slots__ = ("_site",)

    def __init__(self, site: Site):
        self._site = site

    def __getattr__(self, name: str) -> list:
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        return self.get(name)

    def get(self, name: str, lang: str = "") -> list:
        """Get menu by name, optionally filtered by language."""
        menu = self._site.menu.get(name, [])
        return [item.to_dict() if hasattr(item, "to_dict") else item for item in menu]


def build_page_context(
    page: Page | SimpleNamespace,
    site: Site,
    content: str = "",
    *,
    section: Any = None,
    element: Any = None,
    posts: list | None = None,
    subsections: list | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build complete template context for any page type.

    This is the SINGLE SOURCE OF TRUTH for all template contexts.
    All rendering paths must use this function.

    Used by:
    - Renderer.render_page() for regular pages
    - RenderingPipeline._render_autodoc_page() for autodoc pages
    - SpecialPagesGenerator for 404/search/graph pages

    Args:
        page: Page object or SimpleNamespace (synthetic pages)
        site: Site instance
        content: Rendered HTML content
        section: Optional section override (defaults to page._section)
        element: Optional autodoc element (for autodoc pages)
        posts: Override posts list (for generated pages)
        subsections: Override subsections list
        extra: Additional context variables

    Returns:
        Complete template context dict with all wrappers applied

    Example:
        context = build_page_context(page, site, content=html)
        rendered = template.render(**context)
    """
    # Get metadata - works for both Page and SimpleNamespace
    metadata = getattr(page, "metadata", {}) or {}

    # Resolve section (from arg, page attribute, or None)
    resolved_section = section
    if resolved_section is None:
        resolved_section = getattr(page, "_section", None) or getattr(page, "section", None)

    # Build cascading params context
    # Cascade: page → section → site (most to least specific)
    section_params = {}
    if resolved_section and hasattr(resolved_section, "metadata"):
        section_params = resolved_section.metadata or {}

    site_params = site.config.get("params", {})

    # Build smart context objects
    theme_obj = site.theme_config if hasattr(site, "theme_config") else None

    context: dict[str, Any] = {
        # Layer 1: Globals (smart wrappers)
        "site": SiteContext(site),
        "config": ConfigContext(site.config),
        "theme": ThemeContext(theme_obj) if theme_obj else ThemeContext._empty(),
        "menus": MenusContext(site),
        # Layer 2: Page context (wrapped where needed)
        "page": page,
        "params": CascadingParamsContext(
            page_params=metadata,
            section_params=section_params,
            site_params=site_params,
        ),
        "metadata": metadata,  # Raw dict for compatibility
        "section": SectionContext(resolved_section),
        # Pre-computed content (marked safe)
        "content": Markup(content) if content else Markup(""),
        "title": getattr(page, "title", "") or "",
        "toc": Markup(getattr(page, "toc", "") or ""),
        "toc_items": getattr(page, "toc_items", []) or [],
        # Pre-computed metadata
        "meta_desc": (
            getattr(page, "meta_description", "") or getattr(page, "description", "") or ""
        ),
        "reading_time": getattr(page, "reading_time", 0) or 0,
        "excerpt": getattr(page, "excerpt", "") or "",
        # Versioning defaults
        "current_version": None,
        "is_latest_version": True,
    }

    # Add section content lists
    if resolved_section:
        # Use override if provided, then pre-filtered _posts, finally section.pages
        context["posts"] = (
            posts
            if posts is not None
            else metadata.get("_posts", getattr(resolved_section, "pages", []))
        )
        context["pages"] = context["posts"]  # Alias
        context["subsections"] = (
            subsections
            if subsections is not None
            else metadata.get("_subsections", getattr(resolved_section, "subsections", []))
        )
    else:
        context["posts"] = posts or []
        context["pages"] = context["posts"]
        context["subsections"] = subsections or []

    # Add autodoc element if provided
    if element:
        context["element"] = element

    # Add versioning context if enabled
    if site.versioning_enabled and hasattr(page, "version") and page.version:
        version_obj = site.get_version(page.version)
        if version_obj:
            context["current_version"] = version_obj.to_dict()
            context["is_latest_version"] = version_obj.latest

    # Merge extra context
    if extra:
        context.update(extra)

    return context


def build_special_page_context(
    title: str,
    description: str,
    url: str,
    site: Site,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build context for special pages (404, search, graph).

    Creates a synthetic page and builds full context.

    Args:
        title: Page title
        description: Page description
        url: Page URL
        site: Site instance
        extra: Additional context variables

    Returns:
        Complete template context
    """
    from bengal.core.page.utils import create_synthetic_page

    page = create_synthetic_page(
        title=title,
        description=description,
        url=url,
        kind="page",
        type="special",
    )

    return build_page_context(page, site, content="", extra=extra)
