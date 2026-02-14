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

import threading
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from kida import Markup

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext as BuildContextType

# Re-export all context classes
from bengal.rendering.context.data_wrappers import (
    CascadingParamsContext,
    ParamsContext,
    SmartDict,
)
from bengal.rendering.context.lazy import LazyPageContext, LazyValue, make_lazy
from bengal.rendering.context.menu_context import MenusContext
from bengal.rendering.context.site_wrappers import (
    ConfigContext,
    SiteContext,
    ThemeContext,
)

# Import snapshot types for direct section handling (no wrapper needed)
from bengal.snapshots.types import NO_SECTION, SectionSnapshot

if TYPE_CHECKING:
    from bengal.protocols import PageLike, SiteLike

__all__ = [
    "NO_SECTION",
    "CascadingParamsContext",
    "ConfigContext",
    # Lazy evaluation
    "LazyPageContext",
    "LazyValue",
    # Menu wrapper
    "MenusContext",
    "ParamsContext",
    # Section types (from snapshots - no wrapper needed)
    "SectionSnapshot",
    # Site wrappers
    "SiteContext",
    # Data wrappers
    "SmartDict",
    "ThemeContext",
    # Context builders
    "build_page_context",
    "build_special_page_context",
    "clear_global_context_cache",
    # Engine globals
    "get_engine_globals",
    # Lazy helper
    "make_lazy",
]


# =============================================================================
# Global Context Caching (Ergonomic Overhead Optimization)
# =============================================================================
# Context wrappers like SiteContext, ConfigContext, ThemeContext, and MenusContext
# are stateless - they just provide ergonomic access to the same underlying objects.
# Creating new instances for every page render is wasteful.
#
# This cache stores a single set of global context wrappers per site instance,
# keyed by the site object's id. This eliminates 4 object allocations per page.
#
# For a 225-page site, this saves ~900 object allocations per build.
#
# Thread-safe: Protected by _context_lock for concurrent parallel rendering.

_global_context_cache: dict[int, dict[str, Any]] = {}
_context_lock = threading.Lock()


# Register cache for centralized cleanup (prevents memory leaks in tests)
def _clear_global_context_cache() -> None:
    """Clear global context cache (registered for test cleanup)."""
    with _context_lock:
        _global_context_cache.clear()


# Register at module import time for automatic lifecycle management
try:
    from bengal.utils.cache_registry import InvalidationReason, register_cache

    register_cache(
        "global_context",
        _clear_global_context_cache,
        invalidate_on={
            InvalidationReason.BUILD_START,  # Always fresh per build
            InvalidationReason.CONFIG_CHANGED,
            InvalidationReason.FULL_REBUILD,
            InvalidationReason.TEST_CLEANUP,
        },
    )
except ImportError:
    # Cache registry not available (shouldn't happen in normal usage)
    pass


def _create_global_contexts(site: SiteLike) -> dict[str, Any]:
    """
    Create fresh global context wrappers for a site.

    Helper function that creates the actual context wrapper objects.
    Used by both _get_global_contexts (global cache) and build-scoped caching.

    Args:
        site: Site instance to wrap

    Returns:
        Dict with context wrappers: site, config, theme, menus

    """
    theme_obj = site.theme_config if hasattr(site, "theme_config") else None
    return {
        "site": SiteContext(site),
        "config": ConfigContext(site.config),
        "theme": ThemeContext(theme_obj) if theme_obj is not None else ThemeContext._empty(),
        "menus": MenusContext(site),
    }


def _get_global_contexts(
    site: SiteLike,
    build_context: BuildContextType | None = None,
) -> dict[str, Any]:
    """
    Get or create cached global context wrappers for a site.

    Global contexts (site, config, theme, menus) are stateless wrappers
    that don't change between page renders. Caching them eliminates
    repeated object allocation overhead.

    If build_context is provided, uses build-scoped caching (RFC: Cache Lifecycle
    Hardening). This ensures cache is isolated to the current build and
    automatically cleared when the build completes, preventing cross-build
    contamination.

    Thread-safe: Uses appropriate locking for safe concurrent access.

    Args:
        site: Site instance to wrap
        build_context: Optional BuildContext for build-scoped caching.
                       If provided, cache is scoped to this build.
                       If None, uses global module-level cache (legacy behavior).

    Returns:
        Dict with cached context wrappers: site, config, theme, menus

    """
    # If build_context provided, use build-scoped caching (preferred)
    if build_context is not None:
        return build_context.get_cached(
            "global_contexts",
            lambda: _create_global_contexts(site),
        )

    # Legacy: global cache keyed by site id
    site_id = id(site)

    # Fast path: check if already cached
    with _context_lock:
        if site_id in _global_context_cache:
            return _global_context_cache[site_id]

        # Build and store under lock
        contexts = _create_global_contexts(site)
        _global_context_cache[site_id] = contexts
        return contexts


def clear_global_context_cache() -> None:
    """
    Clear the global context cache.

    Call this between builds or when site configuration changes.

    Thread-safe: Clears under lock.

    """
    _clear_global_context_cache()


def get_engine_globals(site: SiteLike) -> dict[str, Any]:
    """
    Get all engine-agnostic globals for template engine initialization.

    This is the SINGLE SOURCE OF TRUTH for engine globals.
    Use this in Jinja, Kida, and any future engines.

    Shared globals include:
        - site: SiteContext wrapper for safe {{ site.title }} access
        - config: ConfigContext wrapper for safe {{ config.key }} access
        - theme: ThemeContext wrapper for {{ theme.name }}, {{ theme.has('x') }}
        - menus: MenusContext for menu access
        - _raw_site: Raw Site instance for internal template functions
        - bengal: Metadata dict (capabilities, engine info)
        - versioning_enabled: Whether versioning is active
        - versions: List of available versions
        - getattr: Python's getattr for safe attribute access

    Engine-specific globals (url_for, get_menu, get_menu_lang, breadcrumbs)
    must still be added by each engine after calling this function.

    Implementation Notes:
        - Cached and thread-safe via _get_global_contexts()
        - Uses local imports for metadata to prevent circular dependencies

    Args:
        site: Site instance

    Returns:
        Dict of globals to merge into engine's globals

    Example:
        from bengal.rendering.context import get_engine_globals

        # In engine initialization:
        env.globals.update(get_engine_globals(site))

        # Then add engine-specific globals:
        env.globals["url_for"] = self._url_for
        env.globals["get_menu"] = self._get_menu

    """
    # Reuse existing cached contexts (site, config, theme, menus)
    # This leverages the existing id(site) cache for performance.
    contexts = _get_global_contexts(site)

    # Build metadata with fallback (local import prevents circularity)
    try:
        from bengal.rendering.metadata import build_template_metadata

        bengal_metadata = build_template_metadata(site)
    except Exception:
        bengal_metadata = {"engine": {"name": "Bengal SSG", "version": "unknown"}}

    return {
        # Core context wrappers (from existing cache)
        **contexts,
        # Raw site for internal template functions
        "_raw_site": site,
        # Metadata for templates/JS
        "bengal": bengal_metadata,
        # Versioning
        "versioning_enabled": site.versioning_enabled,
        "versions": site.versions,
        # Python builtin useful in templates
        "getattr": getattr,
    }


def build_page_context(
    page: PageLike | SimpleNamespace,
    site: SiteLike,
    content: str = "",
    *,
    section: Any = None,
    element: Any = None,
    posts: list | None = None,
    subsections: list | None = None,
    extra: dict[str, Any] | None = None,
    snapshot: Any = None,  # SiteSnapshot (optional)
    lazy: bool = True,  # Enable lazy evaluation for expensive fields
    build_context: Any = None,  # BuildContext for O(1) section lookup
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
        snapshot: Optional SiteSnapshot for lock-free rendering (RFC: rfc-bengal-snapshot-engine)
        lazy: Enable lazy evaluation for posts/subsections/toc_items (default True)

    Returns:
        Complete template context dict with all wrappers applied

    Example:
        context = build_page_context(page, site, content=html)
        rendered = template.render(**context)

    Performance:
        With lazy=True (default), posts/subsections/toc_items are only evaluated
        when accessed. This provides 15-25% speedup for simple templates.

    """
    # Get metadata - works for both Page and SimpleNamespace
    metadata = getattr(page, "metadata", {}) or {}

    # Resolve section (from arg, page attribute, or None)
    resolved_section = section
    if resolved_section is None:
        resolved_section = getattr(page, "_section", None) or getattr(page, "section", None)

    # Resolve section to SectionSnapshot (no wrapper needed)
    # SectionSnapshot has params property and __bool__ for template compatibility
    # PERF: Use BuildContext cached lookup for O(1) instead of O(S) iteration
    section_snapshot: SectionSnapshot | None = None

    if isinstance(resolved_section, SectionSnapshot):
        # Already a snapshot
        section_snapshot = resolved_section
    elif resolved_section and build_context:
        # O(1) cached lookup via BuildContext
        result = build_context.get_section_snapshot(resolved_section)
        if result != NO_SECTION:
            section_snapshot = result
    elif snapshot and resolved_section:
        # Fallback: O(S) iteration (when no build_context available)
        for sec_snap in snapshot.sections:
            if sec_snap.path == getattr(resolved_section, "path", None) or sec_snap.name == getattr(
                resolved_section, "name", ""
            ):
                section_snapshot = sec_snap
                break

    # Build cascading params context
    # Cascade: page → section → site (most to least specific)
    section_params = {}
    if section_snapshot:
        section_params = dict(section_snapshot.metadata) if section_snapshot.metadata else {}
    elif resolved_section and hasattr(resolved_section, "metadata"):
        # Legacy path: mutable Section (should rarely happen)
        section_params = resolved_section.metadata or {}

    site_params = site.config.get("params", {})

    # Get cached global contexts (site/config/theme/menus are stateless wrappers)
    global_contexts = _get_global_contexts(site)

    # Use SectionSnapshot directly (no wrapper needed)
    # SectionSnapshot has params property and __bool__ for template compatibility
    # NO_SECTION sentinel used when no section exists
    section_for_context: SectionSnapshot = section_snapshot if section_snapshot else NO_SECTION

    # Use LazyPageContext if lazy evaluation enabled, else standard dict
    context: dict[str, Any] = LazyPageContext() if lazy else {}

    # Layer 1: Globals (cached smart wrappers - no per-page allocation)
    context.update(global_contexts)

    # Layer 2: Page context (wrapped where needed)
    context["page"] = page
    context["params"] = CascadingParamsContext(
        page_params=metadata,
        section_params=section_params,
        site_params=site_params,
    )
    context["metadata"] = metadata  # Raw dict for compatibility
    context["section"] = section_for_context

    # Pre-computed content (marked safe)
    context["content"] = Markup(content) if content else Markup("")
    context["title"] = getattr(page, "title", "") or ""
    context["toc"] = Markup(getattr(page, "toc", "") or "")

    # toc_items - lazy if possible (parsing can be expensive)
    if lazy:
        context["toc_items"] = make_lazy(lambda: getattr(page, "toc_items", []) or [])
    else:
        context["toc_items"] = getattr(page, "toc_items", []) or []

    # Pre-computed metadata (cheap, always eager)
    context["meta_desc"] = (
        getattr(page, "meta_description", "") or getattr(page, "description", "") or ""
    )
    context["word_count"] = getattr(page, "word_count", 0) or 0
    context["reading_time"] = getattr(page, "reading_time", 0) or 0
    context["excerpt"] = getattr(page, "excerpt", "") or ""

    # Versioning defaults
    context["current_version"] = None
    context["is_latest_version"] = True

    # Add section content lists (lazy evaluated - often not accessed)
    if lazy:
        _add_lazy_section_content(
            context, section_snapshot, resolved_section, metadata, posts, subsections
        )
    else:
        _add_eager_section_content(
            context, section_snapshot, resolved_section, metadata, posts, subsections
        )

    # Add autodoc element if provided
    if element:
        context["element"] = element

    # Add versioning context if enabled (lazy - not always accessed)
    if site.versioning_enabled and hasattr(page, "version") and page.version:
        if lazy:
            # Capture version for closure
            page_version = page.version

            def _get_version_context() -> dict[str, Any] | None:
                version_obj = site.get_version(page_version)
                return version_obj.to_dict() if version_obj else None

            def _get_is_latest() -> bool:
                version_obj = site.get_version(page_version)
                return version_obj.latest if version_obj else True

            context["current_version"] = make_lazy(_get_version_context)
            context["is_latest_version"] = make_lazy(_get_is_latest)
        else:
            version_obj = site.get_version(page.version)
            if version_obj:
                context["current_version"] = version_obj.to_dict()
                context["is_latest_version"] = version_obj.latest

    # Merge extra context
    if extra:
        context.update(extra)

    return context


def _add_lazy_section_content(
    context: dict[str, Any],
    section_snapshot: SectionSnapshot | None,
    resolved_section: Any,
    metadata: dict[str, Any],
    posts: list | None,
    subsections: list | None,
) -> None:
    """Add section content lists with lazy evaluation."""
    if section_snapshot and section_snapshot != NO_SECTION:
        # Snapshot path - use lazy evaluation
        if posts is not None:
            context["posts"] = posts
            context["pages"] = posts
        else:
            # Capture section for closure
            sec = section_snapshot
            context["posts"] = make_lazy(lambda: list(sec.sorted_pages))
            context["pages"] = make_lazy(lambda: list(sec.sorted_pages))

        if subsections is not None:
            context["subsections"] = subsections
        else:
            sec = section_snapshot
            context["subsections"] = make_lazy(lambda: list(sec.sorted_subsections))

    elif resolved_section:
        # Legacy path - still use lazy evaluation
        if posts is not None:
            context["posts"] = posts
            context["pages"] = posts
        else:
            sec = resolved_section
            meta = metadata
            context["posts"] = make_lazy(lambda: meta.get("_posts", getattr(sec, "pages", [])))
            context["pages"] = make_lazy(lambda: meta.get("_posts", getattr(sec, "pages", [])))

        if subsections is not None:
            context["subsections"] = subsections
        else:
            sec = resolved_section
            meta = metadata
            context["subsections"] = make_lazy(
                lambda: meta.get("_subsections", getattr(sec, "subsections", [])) or []
            )
    else:
        context["posts"] = posts or []
        context["pages"] = posts or []
        context["subsections"] = subsections or []


def _add_eager_section_content(
    context: dict[str, Any],
    section_snapshot: SectionSnapshot | None,
    resolved_section: Any,
    metadata: dict[str, Any],
    posts: list | None,
    subsections: list | None,
) -> None:
    """Add section content lists with eager evaluation (legacy behavior)."""
    if section_snapshot and section_snapshot != NO_SECTION:
        context["posts"] = posts if posts is not None else list(section_snapshot.sorted_pages)
        context["pages"] = context["posts"]
        context["subsections"] = (
            subsections if subsections is not None else list(section_snapshot.sorted_subsections)
        )
    elif resolved_section:
        context["posts"] = (
            posts
            if posts is not None
            else metadata.get("_posts", getattr(resolved_section, "pages", []))
        )
        context["pages"] = context["posts"]
        raw_subsections = (
            subsections
            if subsections is not None
            else metadata.get("_subsections", getattr(resolved_section, "subsections", []))
        )
        context["subsections"] = raw_subsections if raw_subsections else []
    else:
        context["posts"] = posts or []
        context["pages"] = context["posts"]
        context["subsections"] = subsections or []


def build_special_page_context(
    title: str,
    description: str,
    url: str,
    site: SiteLike,
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
