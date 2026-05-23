"""
Unified icon resolution for all Bengal icon consumers.

This module provides centralized icon loading with theme-aware resolution.
All icon loading (template functions, plugins, directives) should use this module.

Resolution Order (first match wins):
    1. site/themes/{theme}/assets/icons/{name}.svg   ← Site overrides (highest)
    2. bengal/themes/{theme}/assets/icons/{name}.svg ← Theme's custom icons
    3. bengal/themes/{parent}/assets/icons/{name}.svg ← Parent theme (if extended)
    4. bengal/themes/default/assets/icons/{name}.svg ← Bengal defaults (lowest)

Usage:
    >>> from bengal.icons import resolver
    >>> resolver.initialize(site)
    >>> svg_content = resolver.load_icon("warning")
    >>> paths = resolver.get_search_paths()  # For error messages
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bengal.protocols import SiteConfig

logger = get_logger(__name__)

__all__ = [
    "clear_cache",
    "get_available_icons",
    "get_scope_key",
    "get_search_paths",
    "initialize",
    "load_icon",
    "site_context",
]

# Legacy default state (set during Site initialization). Scoped rendering paths
# should use site_context() or pass site=... to avoid cross-site contamination.
# Thread-safe: All state access protected by _icon_lock for concurrent access.
_icon_lock = threading.Lock()
_search_paths: list[Path] = []
_icon_cache: dict[str, str] = {}
_not_found_cache: set[str] = set()  # Avoid repeated disk checks
_initialized: bool = False


@dataclass
class _IconResolverState:
    """Per-search-path icon resolver cache."""

    search_paths: tuple[Path, ...]
    icon_cache: dict[str, str] = field(default_factory=dict)
    not_found_cache: set[str] = field(default_factory=set)

    @property
    def scope_key(self) -> tuple[str, ...]:
        return tuple(str(path) for path in self.search_paths)


_scoped_states: dict[tuple[str, ...], _IconResolverState] = {}
_active_state: ContextVar[_IconResolverState | None] = ContextVar(
    "bengal_icon_resolver_state",
    default=None,
)

# Characters that are not allowed in icon names (path traversal prevention)
_INVALID_CHARS = frozenset("/\\.\x00")


def _is_valid_icon_name(name: str) -> bool:
    """
    Validate icon name to prevent path traversal attacks.

    Rejects names containing:
    - Path separators (/ or \\)
    - Directory traversal characters (.)
    - Null bytes

    Args:
        name: Icon name to validate

    Returns:
        True if the name is safe, False otherwise

    """
    if not name:
        return False
    # Check for any invalid characters
    return not any(c in _INVALID_CHARS for c in name)


def initialize(site: SiteConfig, preload: bool = False) -> None:
    """
    Initialize icon resolver with Site context.

    Called once during Site initialization, before any rendering.
    Sets up search paths based on theme configuration.

    Thread-safe: Atomically updates all state under lock.

    Args:
        site: Site instance for theme resolution
        preload: If True, eagerly load all icons (production mode)

    """
    global _search_paths, _initialized
    # Compute paths outside lock (expensive I/O)
    paths = _get_icon_search_paths(site)
    state = _get_or_create_state(paths)

    with _icon_lock:
        _search_paths = paths
        _icon_cache.clear()
        _not_found_cache.clear()
        state.icon_cache.clear()
        state.not_found_cache.clear()
        _initialized = True

    if preload:
        _preload_state(state)
        _preload_all_icons()


def _get_or_create_state(paths: list[Path] | tuple[Path, ...]) -> _IconResolverState:
    """Return the per-scope resolver state for a search path chain."""
    search_paths = tuple(paths)
    key = tuple(str(path) for path in search_paths)
    with _icon_lock:
        state = _scoped_states.get(key)
        if state is None:
            state = _IconResolverState(search_paths=search_paths)
            _scoped_states[key] = state
        return state


def _state_for_site(site: SiteConfig) -> _IconResolverState:
    return _get_or_create_state(_get_icon_search_paths(site))


@contextmanager
def site_context(site: SiteConfig) -> Iterator[None]:
    """Temporarily scope icon resolution to a site/theme search path chain."""
    state = _state_for_site(site)
    token: Token[_IconResolverState | None] = _active_state.set(state)
    try:
        yield
    finally:
        _active_state.reset(token)


def _get_icon_search_paths(site: SiteConfig) -> list[Path]:
    """
    Get ordered list of icon directories to search.

    Returns directories from highest to lowest priority:
    1. Site theme icons (site/themes/{theme}/assets/icons)
    2. Theme icons with inheritance chain
    3. Default theme icons (if extend_defaults=True)

    """
    from bengal.services.theme import get_theme_assets_chain

    paths: list[Path] = []

    # Get theme asset chain (handles inheritance)
    # Returns paths from parent → child, we want child → parent for lookup
    for assets_dir in reversed(get_theme_assets_chain(site.root_path, site.theme)):
        icons_dir = assets_dir / "icons"
        if icons_dir.exists() and icons_dir not in paths:
            paths.append(icons_dir)

    # Add default theme if extending (default behavior)
    extend_defaults = True
    if hasattr(site, "theme_config") and site.theme_config is not None:
        icons_config = getattr(site.theme_config, "icons", None)
        if icons_config is not None:
            extend_defaults = getattr(icons_config, "extend_defaults", True)

    if extend_defaults:
        import bengal

        bengal_file = bengal.__file__
        if bengal_file is not None:
            default_icons = Path(bengal_file).parent / "themes" / "default" / "assets" / "icons"
            if default_icons.exists() and default_icons not in paths:
                paths.append(default_icons)

    return paths


def _get_fallback_path() -> Path:
    """Get fallback icon path when resolver not initialized."""
    import bengal

    bengal_file = bengal.__file__
    if bengal_file is None:
        raise RuntimeError("Bengal package __file__ is None, cannot determine icon path")
    return Path(bengal_file).parent / "themes" / "default" / "assets" / "icons"


def load_icon(name: str, *, site: SiteConfig | None = None) -> str | None:
    """
    Load icon from first matching path in search chain.

    Uses caching to avoid repeated disk I/O:
    - Found icons cached by content
    - Not-found icons cached to skip repeated searches

    Security: Validates icon name to prevent path traversal attacks.

    Thread-safe: Cache reads/writes protected by lock.

    Args:
        name: Icon name (without .svg extension)

    Returns:
        SVG content string, or None if not found

    """
    # Validate icon name to prevent path traversal attacks
    if not _is_valid_icon_name(name):
        logger.debug(
            "icon_name_invalid",
            icon=name,
            reason="contains invalid characters (path traversal prevention)",
        )
        return None

    state = _state_for_site(site) if site is not None else _active_state.get()

    if state is not None:
        return _load_icon_from_state(name, state)

    # Legacy fallback for callers outside an explicit site/build scope.
    with _icon_lock:
        if name in _icon_cache:
            return _icon_cache[name]

        if name in _not_found_cache:
            return None

        # Copy search paths under lock for safe iteration outside lock
        search_paths = _search_paths.copy() if _initialized else [_get_fallback_path()]

    # Expensive I/O outside lock
    for icons_dir in search_paths:
        icon_path = icons_dir / f"{name}.svg"
        if icon_path.exists():
            try:
                content = icon_path.read_text(encoding="utf-8")
                with _icon_lock:
                    _icon_cache[name] = content
                return content
            except OSError as e:
                logger.debug(
                    "icon_read_error",
                    icon=name,
                    path=str(icon_path),
                    error=str(e),
                )
                continue

    logger.debug(
        "icon_not_found_in_resolver",
        icon=name,
        search_paths=[str(p) for p in search_paths],
    )
    with _icon_lock:
        _not_found_cache.add(name)
    return None


def _load_icon_from_state(name: str, state: _IconResolverState) -> str | None:
    """Load an icon using a site-scoped resolver state."""
    with _icon_lock:
        if name in state.icon_cache:
            return state.icon_cache[name]
        if name in state.not_found_cache:
            return None
        search_paths = state.search_paths

    for icons_dir in search_paths:
        icon_path = icons_dir / f"{name}.svg"
        if icon_path.exists():
            try:
                content = icon_path.read_text(encoding="utf-8")
                with _icon_lock:
                    state.icon_cache[name] = content
                return content
            except OSError as e:
                logger.debug(
                    "icon_read_error",
                    icon=name,
                    path=str(icon_path),
                    error=str(e),
                )
                continue

    logger.debug(
        "icon_not_found_in_resolver",
        icon=name,
        search_paths=[str(p) for p in search_paths],
    )
    with _icon_lock:
        state.not_found_cache.add(name)
    return None


def get_search_paths() -> list[Path]:
    """
    Get current search paths (for error messages).

    Thread-safe: Returns copy under lock.

    Returns:
        Copy of the current search paths list

    """
    state = _active_state.get()
    if state is not None:
        return list(state.search_paths)

    with _icon_lock:
        if _initialized:
            return _search_paths.copy()
    return [_get_fallback_path()]


def get_scope_key(site: SiteConfig | None = None) -> tuple[str, ...]:
    """Return the active icon resolver scope key for render-cache namespacing."""
    if site is not None:
        return _state_for_site(site).scope_key
    state = _active_state.get()
    if state is not None:
        return state.scope_key
    with _icon_lock:
        if _initialized:
            return tuple(str(path) for path in _search_paths)
    return (str(_get_fallback_path()),)


def get_available_icons() -> list[str]:
    """
    Get list of all available icon names across search paths.

    Returns icon names in priority order (higher priority first).
    Duplicates are included only once (first occurrence wins).

    Thread-safe: Copies search paths under lock.

    Returns:
        List of icon names (without .svg extension)

    """
    seen: set[str] = set()
    icons: list[str] = []

    state = _active_state.get()
    if state is not None:
        search_paths = list(state.search_paths)
    else:
        # Copy search paths under lock
        with _icon_lock:
            search_paths = _search_paths.copy() if _initialized else [_get_fallback_path()]

    # Disk I/O outside lock
    for icons_dir in search_paths:
        if icons_dir.exists():
            for icon_path in sorted(icons_dir.glob("*.svg")):
                name = icon_path.stem
                if name not in seen:
                    icons.append(name)
                    seen.add(name)

    return icons


def clear_cache() -> None:
    """
    Clear icon cache (for dev server hot reload).

    Call this when theme assets change to reload modified icons.

    Thread-safe: Clears under lock.

    """
    with _icon_lock:
        _icon_cache.clear()
        _not_found_cache.clear()
        for state in _scoped_states.values():
            state.icon_cache.clear()
            state.not_found_cache.clear()


def _preload_all_icons() -> None:
    """
    Preload all icons from search paths (production optimization).

    Scans all icon directories and loads SVG content into cache.
    First match wins for duplicate icon names.

    Thread-safe: Cache writes protected by lock.

    """
    # Copy search paths under lock
    with _icon_lock:
        search_paths = _search_paths.copy()

    seen: set[str] = set()
    loaded: dict[str, str] = {}

    # Disk I/O outside lock
    for icons_dir in search_paths:
        if not icons_dir.exists():
            continue
        for icon_path in icons_dir.glob("*.svg"):
            name = icon_path.stem
            if name not in seen:  # First match wins
                try:
                    loaded[name] = icon_path.read_text(encoding="utf-8")
                    seen.add(name)
                except OSError as e:
                    logger.debug(
                        "icon_preload_error",
                        icon=name,
                        path=str(icon_path),
                        error=str(e),
                    )

    # Batch update cache under lock
    with _icon_lock:
        _icon_cache.update(loaded)


def _preload_state(state: _IconResolverState) -> None:
    """Preload all icons into a site-scoped resolver state."""
    search_paths = state.search_paths
    seen: set[str] = set()
    loaded: dict[str, str] = {}

    for icons_dir in search_paths:
        if not icons_dir.exists():
            continue
        for icon_path in icons_dir.glob("*.svg"):
            name = icon_path.stem
            if name in seen:
                continue
            try:
                loaded[name] = icon_path.read_text(encoding="utf-8")
                seen.add(name)
            except OSError as e:
                logger.debug(
                    "icon_preload_error",
                    icon=name,
                    path=str(icon_path),
                    error=str(e),
                )

    with _icon_lock:
        state.icon_cache.update(loaded)


def is_initialized() -> bool:
    """Check if resolver has been initialized with a Site."""
    with _icon_lock:
        return _initialized
