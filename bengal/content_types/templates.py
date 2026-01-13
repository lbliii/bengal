"""
Template resolution utilities for content types.

Provides centralized template cascade logic that was previously
duplicated across content type strategies.

Functions:
    resolve_template_cascade: Find first existing template from candidates
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.rendering.engines.protocol import TemplateEngineProtocol

logger = get_logger(__name__)


def resolve_template_cascade(
    candidates: list[str],
    template_engine: TemplateEngineProtocol | None,
    fallback: str = "single.html",
) -> str:
    """
    Resolve template from cascade of candidates.
    
    Tries each candidate in order, returning first that exists.
    Falls back to specified default if none exist.
    
    Args:
        candidates: Template names to try in order
        template_engine: Engine for existence checks
        fallback: Default template if none found
    
    Returns:
        First existing template or fallback
    
    Example:
            >>> from bengal.content_types.templates import resolve_template_cascade
            >>> template = resolve_template_cascade(
            ...     ["blog/home.html", "home.html", "index.html"],
            ...     engine,
            ...     fallback="index.html"
            ... )
        
    """
    if template_engine is None:
        logger.debug("template_cascade_no_engine", fallback=fallback)
        return fallback

    for candidate in candidates:
        if template_engine.template_exists(candidate):
            logger.debug(
                "template_cascade_resolved",
                template=candidate,
                candidates_tried=candidates[: candidates.index(candidate) + 1],
            )
            return candidate

    logger.debug(
        "template_cascade_fallback",
        candidates=candidates,
        fallback=fallback,
    )
    return fallback
