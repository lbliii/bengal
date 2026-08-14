"""Kida capabilities, template introspection, and cache operations."""

from __future__ import annotations

from typing import Any

from bengal.protocols import EngineCapability
from bengal.protocols.capabilities import has_clear_template_cache


def capabilities(engine: Any) -> EngineCapability:
    """
    Return Kida engine capabilities.

    Kida supports all advanced features:
    - Block caching for efficient re-rendering
    - Block-level change detection for incremental builds
    - Template introspection for dependency analysis
    - Pipeline operators (|>) for functional transformations
    - Pattern matching (match/case) in templates
    """
    return (
        EngineCapability.BLOCK_CACHING
        | EngineCapability.BLOCK_LEVEL_DETECTION
        | EngineCapability.INTROSPECTION
        | EngineCapability.PIPELINE_OPERATORS
        | EngineCapability.PATTERN_MATCHING
    )


def has_capability(engine: Any, cap: EngineCapability) -> bool:
    """Check if Kida has a specific capability."""
    return cap in engine.capabilities


def get_template_introspection(engine: Any, name: str) -> dict[str, Any] | None:
    """Get introspection metadata for a template.

    Returns analysis of template structure including:
    - blocks: Block metadata (dependencies, purity, cache scope)
    - extends: Parent template name (if any)
    - all_dependencies: All context paths the template accesses

    Args:
        name: Template identifier (e.g., "page.html")

    Returns:
        Dict with template metadata, or None if:
        - Template not found
        - AST was not preserved (preserve_ast=False)

    Example:
        >>> info = engine.get_template_introspection("page.html")
        >>> if info:
        ...     for block_name, meta in info["blocks"].items():
        ...         if meta.cache_scope == "site":
        ...             print(f"Block {block_name} is site-cacheable")
    """
    try:
        template = engine._env.get_template(name)
        meta = template.template_metadata()
        if meta is None:
            return None

        return {
            "name": meta.name,
            "extends": meta.extends,
            "blocks": meta.blocks,
            "all_dependencies": meta.all_dependencies(),
        }
    except Exception:
        return None


def get_cacheable_blocks(engine: Any, name: str) -> dict[str, str]:
    """Get blocks that can be cached and their cache scope.

    Convenience method for build optimization. Returns only blocks
    with determined cache scope (excludes "unknown").

    Args:
        name: Template identifier

    Returns:
        Dict of block_name → cache_scope ("site" or "page")

    Example:
        >>> cacheable = engine.get_cacheable_blocks("base.html")
        >>> # {'nav': 'site', 'footer': 'site', 'content': 'page'}
    """
    info = engine.get_template_introspection(name)
    if not info:
        return {}

    return {
        block_name: meta.cache_scope
        for block_name, meta in info["blocks"].items()
        if meta.cache_scope in ("site", "page") and meta.is_pure == "pure"
    }


def get_template_profile(engine: Any) -> dict[str, Any] | None:
    """Get template profiling report.

    Returns:
        Dictionary with timing statistics, or None if profiling disabled.
    """
    if engine._profiler:
        return engine._profiler.get_report()
    return None


def clear_template_cache(engine: Any, names: list[str] | None = None) -> None:
    """Clear template cache for external invalidation.

    Called by TemplateChangeDetector when template files change to force
    cache invalidation without waiting for hash checks.

    Args:
        names: Optional list of template names to clear.
               If None, clears all cached templates.

    Example:
        >>> engine.clear_template_cache()  # Clear all
        >>> engine.clear_template_cache(["base.html", "page.html"])  # Specific
    """
    if has_clear_template_cache(engine._env):
        engine._env.clear_template_cache(names)


def precompile_templates(engine: Any, template_names: list[str] | None = None) -> int:
    """Pre-compile templates to warm the cache.

    Compiles templates ahead of rendering to avoid compile-on-demand
    overhead during the render phase. This is especially beneficial
    when using bytecode caching (templates are compiled and cached to disk).

    Args:
        template_names: Optional list of template names to precompile.
                       If None, precompiles all templates in template_dirs.

    Returns:
        Number of templates compiled

    Example:
        >>> # Precompile all templates at build start
        >>> count = engine.precompile_templates()
        >>> print(f"Precompiled {count} templates")
    """
    templates = template_names or engine.list_templates()
    compiled = 0

    for name in templates:
        try:
            engine._env.get_template(name)
            compiled += 1
        except Exception:  # noqa: S110
            # Skip templates that fail to compile
            # (will be caught later during rendering)
            pass

    return compiled


def cache_info(engine: Any) -> dict[str, Any]:
    """Get cache statistics for monitoring.

    Returns:
        Dict with template, fragment, and bytecode cache stats

    Example:
        >>> info = engine.cache_info()
        >>> print(f"Template hits: {info['template']['hits']}")
        >>> print(f"Fragment hits: {info['fragment']['hits']}")
    """
    if hasattr(engine._env, "cache_info"):
        return engine._env.cache_info()
    return {}
