"""
Data wrapper classes for safe template access patterns.

These classes provide ergonomic dict-like access with sensible defaults,
eliminating the need for defensive .get() calls in templates.
"""

from __future__ import annotations

from collections.abc import ItemsView, Iterator, KeysView, ValuesView
from typing import Any


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

    def keys(self) -> KeysView[str]:
        """Return keys view."""
        return self._data.keys()

    def values(self) -> ValuesView[Any]:
        """Return values view."""
        return self._data.values()

    def items(self) -> ItemsView[str, Any]:
        """Return items view."""
        return self._data.items()


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

    __slots__ = ("_cache", "_data")

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
        """Get with explicit default (cached for nested dicts)."""
        value = self._data.get(key)
        if value is None:
            return default
        if isinstance(value, dict):
            # Use same cache as __getattr__ for consistency
            cache = object.__getattribute__(self, "_cache")
            if key not in cache:
                cache[key] = ParamsContext(value)
            return cache[key]
        return value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __bool__(self) -> bool:
        return bool(self._data)

    def __iter__(self) -> Iterator[str]:
        """Iterate over keys."""
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def keys(self) -> KeysView[str]:
        """Return keys view."""
        data: dict[str, Any] = object.__getattribute__(self, "_data")
        return data.keys()

    def values(self) -> ValuesView[Any]:
        """Return values view."""
        data: dict[str, Any] = object.__getattribute__(self, "_data")
        return data.values()

    def items(self) -> ItemsView[str, Any]:
        """Return items view."""
        data: dict[str, Any] = object.__getattribute__(self, "_data")
        return data.items()

    def __repr__(self) -> str:
        data: dict[str, Any] = object.__getattribute__(self, "_data")
        return f"ParamsContext({data!r})"


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

    __slots__ = ("_cache", "_page", "_section", "_site")

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

    def __iter__(self) -> Iterator[str]:
        """Iterate over all keys from all levels."""
        page = object.__getattribute__(self, "_page")
        section = object.__getattribute__(self, "_section")
        site = object.__getattribute__(self, "_site")

        seen: set[str] = set()
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

    def keys(self) -> set[str]:
        """Return all keys from all cascade levels."""
        page = object.__getattribute__(self, "_page")
        section = object.__getattribute__(self, "_section")
        site = object.__getattribute__(self, "_site")
        return set(page.keys()) | set(section.keys()) | set(site.keys())

    def items(self) -> ItemsView[str, Any]:
        """Return items with cascade resolution."""
        page = object.__getattribute__(self, "_page")
        section = object.__getattribute__(self, "_section")
        site = object.__getattribute__(self, "_site")

        result: dict[str, Any] = {}
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
