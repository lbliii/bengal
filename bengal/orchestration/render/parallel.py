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

import threading
from typing import TYPE_CHECKING, Any

from bengal.utils.concurrency import is_gil_disabled

if TYPE_CHECKING:
    from collections.abc import Callable

    from bengal.rendering.pipeline import RenderingPipeline

# Thread-local storage for pipelines (reuse per thread, not per page!)
thread_local = threading.local()


def is_free_threaded() -> bool:
    """
    Detect if running on free-threaded Python (PEP 703).

    Free-threaded Python (python3.13t+) has the GIL disabled, allowing
    true parallel execution with ThreadPoolExecutor.

    Thin alias over the canonical
    :func:`bengal.utils.concurrency.is_gil_disabled`. Kept so the
    ``is_free_threaded`` symbol (re-exported from
    ``bengal.orchestration.render``) keeps resolving for existing callers.

    Returns:
        True if running on free-threaded Python, False otherwise
    """
    return is_gil_disabled()


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
