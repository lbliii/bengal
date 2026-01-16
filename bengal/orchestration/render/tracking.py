"""
Render tracking and cache lifecycle management.

This module provides thread-safe tracking of active render operations
and build generation management for cache invalidation.

RFC: Cache Lifecycle Hardening - Phase 4
"""

from __future__ import annotations

import threading

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

# Build generation counter - incremented each render pass to invalidate stale pipelines
# Each thread's pipeline stores the generation it was created for; if it doesn't match
# the current generation, the pipeline is recreated with a fresh TemplateEngine.
_build_generation: int = 0
_generation_lock = threading.Lock()

# Active render tracking (RFC: Cache Lifecycle Hardening - Phase 4)
# Prevents cache invalidation during active render operations
_active_render_count: int = 0
_active_render_lock = threading.Lock()


def increment_active_renders() -> None:
    """
    Increment active render count (call at render start).

    RFC: Cache Lifecycle Hardening - Phase 4
    Thread-safe counter for tracking active render operations.
    """
    global _active_render_count
    with _active_render_lock:
        _active_render_count += 1


def decrement_active_renders() -> None:
    """
    Decrement active render count (call at render end).

    RFC: Cache Lifecycle Hardening - Phase 4
    Thread-safe counter for tracking active render operations.
    """
    global _active_render_count
    with _active_render_lock:
        if _active_render_count <= 0:
            logger.warning(
                "decrement_active_renders_underflow",
                current_count=_active_render_count,
                hint="Possible mismatched increment/decrement calls",
            )
            return
        _active_render_count -= 1


def get_active_render_count() -> int:
    """
    Get current active render count (for debugging/testing).

    Returns:
        Number of active render operations
    """
    with _active_render_lock:
        return _active_render_count


def increment_build_generation() -> None:
    """
    Increment build generation counter.

    Called at the start of each build to invalidate stale pipelines.
    """
    global _build_generation
    with _generation_lock:
        _build_generation += 1


def get_current_generation() -> int:
    """Get the current build generation (thread-safe)."""
    with _generation_lock:
        return _build_generation


def clear_thread_local_pipelines() -> None:
    """
    Invalidate thread-local pipeline caches across all threads.

    IMPORTANT: Call this at the start of each build to prevent stale
    TemplateEngine/Jinja2 environments from persisting across rebuilds.
    Without this, template changes may not be reflected because the old
    Jinja2 environment with its internal cache would be reused.

    This works by incrementing a global generation counter. Worker threads
    check this counter and recreate their pipelines when it changes.

    RFC: Cache Lifecycle Hardening - Phase 4
    Warning: Should not be called while renders are active. If called during
    active renders, logs a warning but proceeds (defensive behavior).
    """
    # Check for active renders (RFC: Cache Lifecycle Hardening)
    with _active_render_lock:
        if _active_render_count > 0:
            logger.warning(
                "clear_pipelines_during_active_render",
                active_count=_active_render_count,
                hint="This may cause inconsistent render results",
            )
            # In strict mode, could raise RuntimeError here
            # For now, log warning and proceed (defensive)

    increment_build_generation()


# Register thread-local pipeline cache with centralized cache registry
try:
    from bengal.utils.cache_registry import InvalidationReason, register_cache

    register_cache(
        "thread_local_pipelines",
        clear_thread_local_pipelines,
        invalidate_on={
            InvalidationReason.TEMPLATE_CHANGE,
            InvalidationReason.FULL_REBUILD,
            InvalidationReason.TEST_CLEANUP,
        },
    )
except ImportError:
    # Cache registry not available (shouldn't happen in normal usage)
    pass
