"""
Rendering orchestration for Bengal SSG.

This package handles page rendering in both sequential and parallel modes.
Supports free-threaded Python for true parallelism and falls back to
sequential rendering on standard Python.

Key Modules:
    - orchestrator: Main RenderOrchestrator class
    - parallel: Free-threaded detection and thread-local pipelines
    - tracking: Active render tracking and build generation management

API Compatibility:
    Import RenderOrchestrator from this package:
        from bengal.orchestration.render import RenderOrchestrator

Related Modules:
    - bengal.rendering.template_engine: Template rendering implementation
    - bengal.rendering.renderer: Individual page rendering logic
    - bengal.build.tracking: Dependency graph construction
"""

from .orchestrator import RenderOrchestrator
from .parallel import get_or_create_pipeline, is_free_threaded, thread_local
from .tracking import (
    clear_thread_local_pipelines,
    decrement_active_renders,
    get_active_render_count,
    get_current_generation,
    increment_active_renders,
    increment_build_generation,
)

# Re-export deprecated names for backward compatibility
_get_current_generation = get_current_generation
_increment_active_renders = increment_active_renders
_decrement_active_renders = decrement_active_renders
_is_free_threaded = is_free_threaded
_thread_local = thread_local

__all__ = [
    "RenderOrchestrator",
    # Parallel utilities
    "is_free_threaded",
    "thread_local",
    "get_or_create_pipeline",
    # Tracking utilities
    "clear_thread_local_pipelines",
    "increment_active_renders",
    "decrement_active_renders",
    "get_active_render_count",
    "increment_build_generation",
    "get_current_generation",
    # Deprecated names (for backward compatibility)
    "_get_current_generation",
    "_increment_active_renders",
    "_decrement_active_renders",
    "_is_free_threaded",
    "_thread_local",
]
