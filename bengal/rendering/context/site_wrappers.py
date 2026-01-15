"""
Site-level context wrappers for templates.

Provides ergonomic access to Site, Theme, and Config objects with sensible defaults.

RFC: rfc-incremental-build-dependency-gaps (Phase 1)
- SiteContext.data returns TrackedData wrapper when tracker is available
- Enables automatic data file dependency tracking during template rendering
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.rendering.context.data_wrappers import ParamsContext, SmartDict

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.theme import Theme


class SiteContext:
    """
    Smart wrapper for Site object with ergonomic access patterns.
    
    Provides clean access to site configuration with sensible defaults.
    All properties return safe values (never None for strings).
    
    Data File Tracking:
        When accessing `site.data`, returns a TrackedData wrapper that
        records data file dependencies for incremental builds. This is
        automatic when a DependencyTracker is set via tracker_context().
    
    Example:
        {{ site.title }}             # Site title
        {{ site.logo }}              # Logo URL ('' if not set)
        {{ site.baseurl }}           # Base URL ('' if not set)
        {{ site.author }}            # Default author
        {{ site.params.repo_url }}   # Custom params
        {{ site.data.team }}         # Data file (tracked for incremental builds)
        
    """

    __slots__ = ("_site", "_params_cache", "_tracked_data_cache")

    def __init__(self, site: Site):
        self._site = site
        self._params_cache: ParamsContext | None = None
        self._tracked_data_cache: Any = None

    def __getattr__(self, name: str) -> Any:
        """Proxy to underlying site, with safe fallbacks."""
        # For wrapper's own underscore attrs, use normal attribute access
        if name == "_site":
            return object.__getattribute__(self, "_site")

        # Special handling for 'data' - wrap with TrackedData if tracker available
        if name == "data":
            return self._get_tracked_data()

        # Check for property on site first (including underscore attrs like _dev_menu_metadata)
        if hasattr(self._site, name):
            return getattr(self._site, name)

        # Fall back to config lookup for non-underscore names
        if not name.startswith("_"):
            return self._site.config.get(name, "")

        # Return None for missing underscore attrs (safer than raising)
        return None

    def _get_tracked_data(self) -> Any:
        """Get site.data wrapped with TrackedData for dependency tracking.
        
        Returns a TrackedData wrapper that will record data file access
        when a tracker is available via get_current_tracker() at access time.
        
        The TrackedData wrapper is cached per-SiteContext instance since
        it looks up the tracker dynamically from ContextVar.
        
        Returns:
            TrackedData wrapper (tracks only when tracker is set)
        """
        from bengal.rendering.context.data_tracking import TrackedData
        
        # Create TrackedData wrapper (cached per-site)
        # TrackedData looks up tracker from ContextVar at access time,
        # so caching is safe even across different page renders.
        if self._tracked_data_cache is None:
            data_dir = self._site.root_path / "data"
            self._tracked_data_cache = TrackedData(
                self._site.data,
                data_dir,
            )
        
        return self._tracked_data_cache

    @property
    def title(self) -> str:
        # Access from site section (supports both Config and dict)
        config = self._site.config
        if hasattr(config, "site"):
            return config.site.title or ""
        site_section = config.get("site", {})
        if isinstance(site_section, dict):
            return site_section.get("title", "") or ""
        return config.get("title", "") or ""

    @property
    def description(self) -> str:
        # Access from site section (supports both Config and dict)
        config = self._site.config
        if hasattr(config, "site"):
            return config.site.description or ""
        site_section = config.get("site", {})
        if isinstance(site_section, dict):
            return site_section.get("description", "") or ""
        return config.get("description", "") or ""

    @property
    def baseurl(self) -> str:
        # Access from site section (supports both Config and dict)
        config = self._site.config
        if hasattr(config, "site"):
            return config.site.baseurl or ""
        site_section = config.get("site", {})
        if isinstance(site_section, dict):
            return site_section.get("baseurl", "") or ""
        return config.get("baseurl", "") or ""

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

        Returns a ParamsContext for safe nested access (cached after first access).

        Example:
            {{ site.params.repo_url }}
            {{ site.params.social.twitter }}
        """
        if self._params_cache is None:
            self._params_cache = ParamsContext(self._site.config.get("params", {}))
        return self._params_cache

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

    __slots__ = ("_theme", "_config_cache")

    def __init__(self, theme: Theme | None):
        self._theme = theme
        self._config_cache: ParamsContext | None = None

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

    # Header configuration properties for ergonomic template access
    @property
    def header_nav_position(self) -> str:
        """Header navigation position ('left' or 'center')."""
        if self._theme is None or self._theme.config is None:
            return "left"
        header = self._theme.config.get("header", {})
        return header.get("nav_position", "left") if isinstance(header, dict) else "left"

    @property
    def header_sticky(self) -> bool:
        """Whether header is sticky (fixed at top on scroll)."""
        if self._theme is None or self._theme.config is None:
            return True
        header = self._theme.config.get("header", {})
        return header.get("sticky", True) if isinstance(header, dict) else True

    @property
    def header_autohide(self) -> bool:
        """Whether header auto-hides on scroll down."""
        if self._theme is None or self._theme.config is None:
            return False
        header = self._theme.config.get("header", {})
        return header.get("autohide", False) if isinstance(header, dict) else False

    @property
    def config(self) -> ParamsContext:
        """Theme config as ParamsContext for safe nested access (cached)."""
        if self._config_cache is None:
            if self._theme is None or self._theme.config is None:
                self._config_cache = ParamsContext({})
            else:
                self._config_cache = ParamsContext(self._theme.config)
        return self._config_cache

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

    __slots__ = ("_config", "_nested_cache")

    def __init__(self, config: dict[str, Any]):
        self._config = config or {}
        self._nested_cache: dict[str, SmartDict] = {}

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return object.__getattribute__(self, name)

        value = self._config.get(name)

        # Wrap nested dicts in SmartDict for chained access (with caching)
        if isinstance(value, dict):
            if name not in self._nested_cache:
                self._nested_cache[name] = SmartDict(value)
            return self._nested_cache[name]

        return value if value is not None else ""

    def __getitem__(self, key: str) -> Any:
        return self.__getattr__(key)

    def get(self, key: str, default: Any = "") -> Any:
        """Get with explicit default."""
        value = self._config.get(key)
        if value is None:
            return default
        if isinstance(value, dict):
            # Use same cache as __getattr__ for consistency
            if key not in self._nested_cache:
                self._nested_cache[key] = SmartDict(value)
            return self._nested_cache[key]
        return value

    def __contains__(self, key: str) -> bool:
        return key in self._config
