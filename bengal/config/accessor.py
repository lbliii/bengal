"""
Configuration accessor with structured access patterns.

This module provides the `Config` and `ConfigSection` classes that enable
type-safe, structured access to configuration data. The config is stored
in a nested structure, and these classes provide ergonomic access patterns
with IDE autocomplete support.

Access patterns:
    >>> cfg = Config(loaded_dict)
    >>> cfg.site.title           # Attribute access (preferred)
    'My Site'
    >>> cfg.build.parallel       # Nested sections
True
    >>> cfg["theme"]["name"]     # Dict access for dynamic keys
    'default'
    >>> cfg.site.get("custom")   # Optional keys (returns None)
None
    >>> cfg.site.typo            # Typos raise AttributeError!
AttributeError: No config key 'typo' in section

See Also:
- :mod:`bengal.config.loader`: Configuration loading.
- :mod:`bengal.config.defaults`: Default configuration values.

"""

from __future__ import annotations

from functools import cached_property
from typing import Any, Protocol, cast

# -----------------------------------------------------------------------------
# Type Protocols (for IDE autocomplete)
# -----------------------------------------------------------------------------


class SiteConfig(Protocol):
    """Type hints for site.* config section."""

    title: str
    baseurl: str
    description: str
    author: str
    language: str


class BuildConfig(Protocol):
    """Type hints for build.* config section."""

    output_dir: str
    content_dir: str
    assets_dir: str
    templates_dir: str
    parallel: bool
    incremental: bool | None
    max_workers: int | None
    pretty_urls: bool
    minify_html: bool
    strict_mode: bool
    debug: bool


class DevConfig(Protocol):
    """Type hints for dev.* config section."""

    cache_templates: bool
    watch_backend: bool
    live_reload: bool
    port: int


# -----------------------------------------------------------------------------
# Config Classes
# -----------------------------------------------------------------------------


class Config:
    """
    Configuration accessor with structured access.
    
    Access patterns:
            >>> cfg = Config(loaded_dict)
            >>> cfg.site.title           # Attribute access (preferred)
            'My Site'
            >>> cfg.build.parallel       # Nested sections
        True
            >>> cfg["theme"]["name"]     # Dict access for dynamic keys
            'default'
            >>> cfg.site.get("custom")   # Optional keys (returns None)
        None
            >>> cfg.site.typo            # Typos raise AttributeError!
        AttributeError: No config key 'typo' in section
        
    """

    __slots__ = ("_data", "__dict__")  # __dict__ needed for cached_property

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    # -------------------------------------------------------------------------
    # Section Accessors (cached for performance)
    # -------------------------------------------------------------------------

    @cached_property
    def site(self) -> SiteConfig:
        """Returns site section cast to SiteConfig protocol for IDE support."""
        return cast(SiteConfig, ConfigSection(self._data.get("site", {}), "site"))

    @cached_property
    def build(self) -> BuildConfig:
        """Returns build section cast to BuildConfig protocol for IDE support."""
        return cast(BuildConfig, ConfigSection(self._data.get("build", {}), "build"))

    @cached_property
    def dev(self) -> DevConfig:
        """Returns dev section cast to DevConfig protocol for IDE support."""
        return cast(DevConfig, ConfigSection(self._data.get("dev", {}), "dev"))

    @cached_property
    def theme(self) -> ConfigSection:
        return ConfigSection(self._data.get("theme", {}), "theme")

    @cached_property
    def search(self) -> ConfigSection:
        return ConfigSection(self._data.get("search", {}), "search")

    @cached_property
    def content(self) -> ConfigSection:
        return ConfigSection(self._data.get("content", {}), "content")

    @cached_property
    def assets(self) -> ConfigSection:
        return ConfigSection(self._data.get("assets", {}), "assets")

    @cached_property
    def output_formats(self) -> ConfigSection:
        return ConfigSection(self._data.get("output_formats", {}), "output_formats")

    @cached_property
    def features(self) -> ConfigSection:
        return ConfigSection(self._data.get("features", {}), "features")

    def __getattr__(self, key: str) -> ConfigSection | Any:
        """
        Enables config.custom_section.key for user-defined sections.

        Fallthrough for any section not explicitly defined as a property.
        Returns ConfigSection for dict values, raw value for non-dict types.
        """
        if key.startswith("_"):
            raise AttributeError(key)
        value = self._data.get(key, {})
        if isinstance(value, dict):
            return ConfigSection(value, key)
        # Return raw value for non-dict types (string, list, etc.)
        return value

    # -------------------------------------------------------------------------
    # Dict Access (for dynamic/custom keys)
    # -------------------------------------------------------------------------

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dict-style assignment for backward compatibility."""
        self._data[key] = value
        # Invalidate cached properties if setting a section
        if key in (
            "site",
            "build",
            "dev",
            "theme",
            "search",
            "content",
            "assets",
            "output_formats",
            "features",
        ):
            if hasattr(self, key):
                delattr(self, key)  # Clear cached_property

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def setdefault(self, key: str, default: Any = None) -> Any:
        """Set default value if key doesn't exist, return value."""
        return self._data.setdefault(key, default)

    def items(self):
        """Return dict items iterator for compatibility."""
        return self._data.items()

    def keys(self):
        """Return dict keys iterator for compatibility."""
        return self._data.keys()

    def values(self):
        """Return dict values iterator for compatibility."""
        return self._data.values()

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __iter__(self):
        """Allow iteration over keys."""
        return iter(self._data)

    @property
    def raw(self) -> dict[str, Any]:
        """Raw config dict for serialization/debugging."""
        return self._data


class ConfigSection:
    """
    Accessor for a config section with attribute access.
    
    Design decisions:
        1. Missing keys raise AttributeError (typos fail loudly)
        2. Use .get(key) for optional keys that may not exist
        3. Nested dicts become cached ConfigSection for chaining
        4. Nested sections are cached to avoid repeated object creation
    
    Example:
        config.theme.syntax_highlighting.css_class_style  # Cached at each level
        
    """

    __slots__ = ("_data", "_path", "_cache")

    def __init__(self, data: dict[str, Any], path: str = "") -> None:
        # Guard against non-dict data (defensive - prevents 'str' has no attribute 'keys' errors)
        if not isinstance(data, dict):
            data = {}
        self._data = data
        self._path = path  # For error messages
        self._cache: dict[str, ConfigSection] = {}  # Cache nested sections

    def __getattr__(self, key: str) -> Any:
        # Prevent infinite recursion on special attributes
        if key.startswith("_"):
            raise AttributeError(key)

        # Check if key exists — fail loudly on typos!
        if key not in self._data:
            path_str = f"{self._path}.{key}" if self._path else key
            raise AttributeError(
                f"No config key '{key}' in section. "
                f"Use .get('{key}') for optional keys. Path: {path_str}"
            )

        value = self._data[key]

        # Wrap nested dicts as ConfigSection (cached)
        if isinstance(value, dict):
            if key not in self._cache:
                nested_path = f"{self._path}.{key}" if self._path else key
                self._cache[key] = ConfigSection(value, nested_path)
            return self._cache[key]

        return value

    def __setattr__(self, key: str, value: Any) -> None:
        """Allow attribute assignment for backward compatibility."""
        # Handle special attributes
        if key.startswith("_") or key in ("_data", "_path", "_cache"):
            object.__setattr__(self, key, value)
            return

        # Allow setting config keys
        if not hasattr(self, "_data"):
            object.__setattr__(self, key, value)
            return

        self._data[key] = value
        # Clear cache if setting a nested dict that was cached
        if key in self._cache:
            del self._cache[key]

    def __getitem__(self, key: str) -> Any:
        """Dict-style access: section["key"]. Raises KeyError if missing."""
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dict-style assignment for backward compatibility."""
        self._data[key] = value
        # Clear cache if setting a nested dict that was cached
        if key in self._cache:
            del self._cache[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Safe access for optional keys. Returns default if missing."""
        value = self._data.get(key, default)
        if isinstance(value, dict):
            nested_path = f"{self._path}.{key}" if self._path else key
            return ConfigSection(value, nested_path)
        return value

    def setdefault(self, key: str, default: Any = None) -> Any:
        """Set default value if key doesn't exist, return value."""
        return self._data.setdefault(key, default)

    def items(self):
        """Return dict items iterator for compatibility."""
        return self._data.items()

    def keys(self):
        """Return dict keys iterator for compatibility."""
        return self._data.keys()

    def values(self):
        """Return dict values iterator for compatibility."""
        return self._data.values()

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __iter__(self):
        """Allow iteration over keys."""
        return iter(self._data)

    def __repr__(self) -> str:
        return f"ConfigSection({self._path or 'root'}: {list(self._data.keys())})"

    def __bool__(self) -> bool:
        """Allow `if config.section:` to check if section has data."""
        return bool(self._data)
