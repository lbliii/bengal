"""
Template engine utilities.

Provides centralized helper functions for common template operations,
reducing duplication across content type strategies and other modules.

Functions:
    safe_template_exists: Null-safe template existence check with optional logging
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.rendering.engines.protocol import TemplateEngineProtocol

logger = get_logger(__name__)


def safe_template_exists(
    template_engine: TemplateEngineProtocol | None,
    name: str,
    *,
    log_failures: bool = False,
) -> bool:
    """
    Check if template exists with null-safety and optional logging.
    
    Centralizes the common pattern of checking template existence
    with graceful handling of missing engine.
    
    Args:
        template_engine: Template engine (may be None)
        name: Template name to check
        log_failures: If True, log debug message when template not found
    
    Returns:
        True if template exists, False otherwise
    
    Example:
            >>> from bengal.rendering.engines.utils import safe_template_exists
            >>> if safe_template_exists(engine, "blog/home.html"):
            ...     return "blog/home.html"
        
    """
    if template_engine is None:
        return False

    result = template_engine.template_exists(name)

    if not result and log_failures:
        logger.debug(
            "template_check_failed",
            template=name,
            engine=type(template_engine).__name__,
        )

    return result
