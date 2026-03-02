"""
Parallel rendering utilities and free-threaded Python detection.

This module provides utilities for parallel rendering including
free-threaded Python detection and thread-local pipeline management.

Key Features:
- Free-threaded Python (PEP 703) detection
- Thread-local storage for rendering pipelines
- Build generation tracking for cache invalidation
"""

from __future__ import annotations

import sys
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.rendering.pipeline import RenderingPipeline

# Thread-local storage for pipelines (reuse per thread, not per page!)
thread_local = threading.local()


def is_free_threaded() -> bool:
    """
    Detect if running on free-threaded Python (PEP 703).

    Free-threaded Python (python3.13t+) has the GIL disabled, allowing
    true parallel execution with ThreadPoolExecutor.

    Returns:
        True if running on free-threaded Python, False otherwise
    """
    # Check if sys._is_gil_enabled() exists and returns False
    if hasattr(sys, "_is_gil_enabled"):
        try:
            return not sys._is_gil_enabled()
        except (AttributeError, TypeError):
            pass

    # Fallback: check sysconfig for Py_GIL_DISABLED
    try:
        import sysconfig

        return sysconfig.get_config_var("Py_GIL_DISABLED") == 1
    except (ImportError, AttributeError):
        pass

    return False


def get_or_create_pipeline(
    current_gen: int,
    create_pipeline_fn: Callable[..., Any],
) -> RenderingPipeline:
    """
    Get or create a thread-local pipeline instance.

    Checks if pipeline exists AND is from current build generation.
    If generation has changed (new build), recreates the pipeline
    to get a fresh TemplateEngine with updated templates.

    Args:
        current_gen: Current build generation
        create_pipeline_fn: Function to create a new pipeline

    Returns:
        Thread-local RenderingPipeline instance
    """
    needs_new_pipeline = (
        not hasattr(thread_local, "pipeline")
        or getattr(thread_local, "pipeline_generation", -1) != current_gen
    )
    if needs_new_pipeline:
        thread_local.pipeline = create_pipeline_fn()
        thread_local.pipeline_generation = current_gen
    return thread_local.pipeline
