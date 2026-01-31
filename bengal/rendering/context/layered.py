"""
Layered context system using ChainMap for zero-copy context stacking.

RFC: Performance optimization for template context building.

Instead of building a complete dict for each page (N pages × full context),
we stack thin layers using ChainMap:

    ┌─────────────────────────────────────────┐
    │  Page Layer (title, content, toc)       │  ← Only this per page
    ├─────────────────────────────────────────┤
    │  Section Layer (section, posts)         │  ← Shared within section
    ├─────────────────────────────────────────┤
    │  Global Layer (site, config, menus)     │  ← Computed once per build
    └─────────────────────────────────────────┘

Benefits:
- O(1) context creation (just stack pointers, no copying)
- Memory: 1 global + S sections + N page deltas (vs N × full)
- Cache-friendly: global layer stays hot in CPU cache

Usage:
    # At build start (once)
    global_layer = build_global_layer(site)
    
    # Per section (cached)
    section_layer = build_section_layer(section, site)
    
    # Per page (thin delta)
    page_layer = build_page_layer(page, content)
    
    # Stack them (zero-copy)
    ctx = LayeredContext(page_layer, section_layer, global_layer)
    template.render(**ctx)

Thread Safety:
    Layers are immutable after creation. Multiple threads can safely
    share global and section layers while each builds its own page layer.

"""

from __future__ import annotations

from collections import ChainMap
from typing import TYPE_CHECKING, Any

from kida import Markup

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site
    from bengal.snapshots.types import SectionSnapshot


class LayeredContext(ChainMap):
    """
    Zero-copy layered context using ChainMap.
    
    Provides dict-like access while stacking layers without copying.
    Lookup falls through from page → section → global.
    
    Example:
        ctx = LayeredContext(page_dict, section_dict, global_dict)
        ctx["site"]     # Falls through to global layer
        ctx["content"]  # Found in page layer
        ctx["posts"]    # Found in section layer
    
    """
    
    __slots__ = ()
    
    def __repr__(self) -> str:
        return f"LayeredContext({len(self.maps)} layers, {len(self)} keys)"


def build_global_layer(
    site: Site,
    *,
    build_context: Any = None,
) -> dict[str, Any]:
    """
    Build the global context layer (computed ONCE per build).
    
    Contains:
    - site: SiteContext wrapper
    - config: ConfigContext wrapper  
    - theme: ThemeContext wrapper
    - menus: MenusContext wrapper
    - bengal: Metadata dict
    - versioning_enabled, versions
    - getattr: Python builtin
    - _raw_site: Raw site for internal use
    
    Args:
        site: Site instance
        build_context: Optional BuildContext for scoped caching
        
    Returns:
        Immutable global context dict (reuse for all pages)
    
    """
    # Import here to avoid circular dependency
    from bengal.rendering.context import _get_global_contexts
    
    # Get cached wrappers (already optimized)
    contexts = _get_global_contexts(site, build_context)
    
    # Build metadata
    try:
        from bengal.rendering.metadata import build_template_metadata
        bengal_metadata = build_template_metadata(site)
    except Exception:
        bengal_metadata = {"engine": {"name": "Bengal SSG", "version": "unknown"}}
    
    return {
        # Core wrappers (stateless, cached)
        **contexts,
        # Raw site for internal template functions
        "_raw_site": site,
        # Metadata
        "bengal": bengal_metadata,
        # Versioning
        "versioning_enabled": site.versioning_enabled,
        "versions": site.versions,
        # Python builtin
        "getattr": getattr,
    }


def build_section_layer(
    section: Section | SectionSnapshot | None,
    site: Site,
    *,
    posts: list | None = None,
    subsections: list | None = None,
) -> dict[str, Any]:
    """
    Build the section context layer (computed once PER SECTION).
    
    Contains:
    - section: SectionSnapshot or sentinel
    - posts/pages: Section's sorted pages (lazy)
    - subsections: Section's sorted subsections (lazy)
    - section_params: Section's cascaded params
    
    Args:
        section: Section or SectionSnapshot
        site: Site instance for params cascade
        posts: Override posts list
        subsections: Override subsections list
        
    Returns:
        Section context dict (reuse for all pages in section)
    
    """
    from bengal.rendering.context.lazy import make_lazy
    from bengal.snapshots.types import NO_SECTION, SectionSnapshot
    
    layer: dict[str, Any] = {}
    
    if section is None:
        layer["section"] = NO_SECTION
        layer["posts"] = []
        layer["pages"] = []
        layer["subsections"] = []
        return layer
    
    # Determine if snapshot or mutable section
    if isinstance(section, SectionSnapshot):
        section_snapshot = section
        layer["section"] = section_snapshot
        
        # Posts/pages - lazy evaluation
        if posts is not None:
            layer["posts"] = posts
            layer["pages"] = posts
        else:
            sec = section_snapshot
            layer["posts"] = make_lazy(lambda s=sec: list(s.sorted_pages))
            layer["pages"] = make_lazy(lambda s=sec: list(s.sorted_pages))
        
        # Subsections - lazy evaluation
        if subsections is not None:
            layer["subsections"] = subsections
        else:
            sec = section_snapshot
            layer["subsections"] = make_lazy(lambda s=sec: list(s.sorted_subsections))
            
    else:
        # Mutable section (legacy path)
        layer["section"] = section
        
        if posts is not None:
            layer["posts"] = posts
            layer["pages"] = posts
        else:
            sec = section
            layer["posts"] = make_lazy(lambda s=sec: getattr(s, "pages", []))
            layer["pages"] = make_lazy(lambda s=sec: getattr(s, "pages", []))
        
        if subsections is not None:
            layer["subsections"] = subsections
        else:
            sec = section
            layer["subsections"] = make_lazy(lambda s=sec: getattr(s, "subsections", []))
    
    return layer


def build_page_layer(
    page: Page,
    content: str = "",
    *,
    metadata: dict[str, Any] | None = None,
    section_params: dict[str, Any] | None = None,
    site_params: dict[str, Any] | None = None,
    element: Any = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the page context layer (unique PER PAGE).
    
    This is the thin delta - only page-specific data.
    
    Contains:
    - page: Page object
    - params: CascadingParamsContext
    - metadata: Raw metadata dict
    - content: Rendered HTML (Markup)
    - title, toc, toc_items
    - meta_desc, word_count, reading_time, excerpt
    - current_version, is_latest_version
    - element (if autodoc)
    
    Args:
        page: Page object
        content: Rendered HTML content
        metadata: Override metadata
        section_params: Section params for cascade
        site_params: Site params for cascade
        element: Autodoc element (if applicable)
        extra: Additional context vars
        
    Returns:
        Page-specific context dict
    
    """
    from bengal.rendering.context import CascadingParamsContext
    from bengal.rendering.context.lazy import make_lazy
    
    # Get metadata
    meta = metadata if metadata is not None else (getattr(page, "metadata", {}) or {})
    sec_params = section_params or {}
    site_p = site_params or {}
    
    layer: dict[str, Any] = {
        # Core page
        "page": page,
        "params": CascadingParamsContext(
            page_params=meta,
            section_params=sec_params,
            site_params=site_p,
        ),
        "metadata": meta,
        
        # Pre-rendered content
        "content": Markup(content) if content else Markup(""),
        "title": getattr(page, "title", "") or "",
        "toc": Markup(getattr(page, "toc", "") or ""),
        
        # Lazy toc_items
        "toc_items": make_lazy(lambda p=page: getattr(p, "toc_items", []) or []),
        
        # Pre-computed metadata
        "meta_desc": (
            getattr(page, "meta_description", "") or 
            getattr(page, "description", "") or ""
        ),
        "word_count": getattr(page, "word_count", 0) or 0,
        "reading_time": getattr(page, "reading_time", 0) or 0,
        "excerpt": getattr(page, "excerpt", "") or "",
        
        # Versioning defaults (overridden if versioned)
        "current_version": None,
        "is_latest_version": True,
    }
    
    # Add autodoc element if provided
    if element is not None:
        layer["element"] = element
    
    # Merge extra context
    if extra:
        layer.update(extra)
    
    return layer


def build_layered_context(
    page: Page,
    site: Site,
    content: str = "",
    *,
    section: Any = None,
    global_layer: dict[str, Any] | None = None,
    section_layer: dict[str, Any] | None = None,
    element: Any = None,
    extra: dict[str, Any] | None = None,
    build_context: Any = None,
) -> LayeredContext:
    """
    Build a complete layered context for a page.
    
    Convenience function that builds/reuses all layers.
    
    For maximum performance, pre-build global_layer once and
    section_layer once per section, then pass them in.
    
    Args:
        page: Page to render
        site: Site instance
        content: Rendered HTML
        section: Section or SectionSnapshot (auto-resolved if None)
        global_layer: Pre-built global layer (built if None)
        section_layer: Pre-built section layer (built if None)
        element: Autodoc element
        extra: Additional context
        build_context: BuildContext for caching
        
    Returns:
        LayeredContext ready for template.render(**ctx)
    
    """
    from bengal.snapshots.types import SectionSnapshot
    
    # Build or reuse global layer
    if global_layer is None:
        global_layer = build_global_layer(site, build_context=build_context)
    
    # Resolve section
    resolved_section = section
    if resolved_section is None:
        resolved_section = getattr(page, "_section", None) or getattr(page, "section", None)
    
    # Build or reuse section layer
    if section_layer is None:
        section_layer = build_section_layer(resolved_section, site)
    
    # Get params for cascade
    section_params = {}
    if isinstance(resolved_section, SectionSnapshot):
        section_params = dict(resolved_section.metadata) if resolved_section.metadata else {}
    elif resolved_section and hasattr(resolved_section, "metadata"):
        section_params = resolved_section.metadata or {}
    
    site_params = site.config.get("params", {})
    
    # Build page layer (unique per page)
    page_layer = build_page_layer(
        page,
        content,
        metadata=getattr(page, "metadata", {}) or {},
        section_params=section_params,
        site_params=site_params,
        element=element,
        extra=extra,
    )
    
    # Stack layers: page → section → global
    return LayeredContext(page_layer, section_layer, global_layer)


# Cache for global and section layers
class LayeredContextCache:
    """
    Cache for pre-built context layers.
    
    Stores:
    - global_layer: Built once per build
    - section_layers: Built once per section (keyed by section path)
    
    Thread-safe: Uses dict operations which are atomic in Python.
    
    """
    
    __slots__ = ("_global_layer", "_section_layers", "_site_id")
    
    def __init__(self) -> None:
        self._global_layer: dict[str, Any] | None = None
        self._section_layers: dict[str, dict[str, Any]] = {}
        self._site_id: int | None = None
    
    def get_global_layer(
        self, 
        site: Site, 
        build_context: Any = None
    ) -> dict[str, Any]:
        """Get or build the global layer."""
        site_id = id(site)
        if self._global_layer is None or self._site_id != site_id:
            self._global_layer = build_global_layer(site, build_context=build_context)
            self._site_id = site_id
            self._section_layers.clear()  # Invalidate section cache
        return self._global_layer
    
    def get_section_layer(
        self,
        section: Any,
        site: Site,
    ) -> dict[str, Any]:
        """Get or build a section layer."""
        if section is None:
            return build_section_layer(None, site)
        
        # Key by section path
        key = getattr(section, "path", None) or str(id(section))
        if key not in self._section_layers:
            self._section_layers[key] = build_section_layer(section, site)
        return self._section_layers[key]
    
    def clear(self) -> None:
        """Clear all cached layers."""
        self._global_layer = None
        self._section_layers.clear()
        self._site_id = None
