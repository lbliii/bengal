"""
Template resolution utilities for content types.

Provides centralized template cascade logic that was previously
duplicated across content type strategies.

Functions:
    classify_page: Classify page as home, list, or single
    build_template_cascade: Build ordered template candidates for a content type
    resolve_template_cascade: Find first existing template from candidates
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import PageLike
    from bengal.protocols import TemplateEngine as TemplateEngineProtocol

logger = get_logger(__name__)

#: Page type literals for template resolution
PageType = Literal["home", "list", "single"]


def classify_page(page: PageLike) -> PageType:
    """
    Classify a page for template resolution.

    Determines whether a page is a home page, section index (list), or
    regular single page based on its attributes.

    Args:
        page: Page to classify.

    Returns:
        PageType literal: "home", "list", or "single".

    Example:
        >>> page_type = classify_page(page)
        >>> if page_type == "home":
        ...     # Use home template
    """
    if page.is_home or page._path == "/":
        return "home"
    if page.source_path.stem == "_index":
        return "list"
    return "single"


def build_template_cascade(
    type_prefix: str,
    page_type: PageType,
    extra_prefixes: list[str] | None = None,
) -> list[str]:
    """
    Build ordered template cascade for a content type.

    Generates a list of template candidates to try in order, based on
    the content type prefix and page classification.

    Args:
        type_prefix: Content type prefix (e.g., "blog", "doc", "autodoc/python").
        page_type: Page classification from classify_page().
        extra_prefixes: Additional prefixes to try before generic fallbacks.
            Useful for nested types like autodoc that have shared parent templates.

    Returns:
        Ordered list of template paths to try.

    Example:
        >>> candidates = build_template_cascade("blog", "single")
        >>> # Returns: ["blog/single.html", "blog/page.html", "single.html", "page.html"]

        >>> candidates = build_template_cascade("autodoc/python", "list", ["autodoc"])
        >>> # Returns: ["autodoc/python/list.html", "autodoc/python/index.html",
        >>> #          "autodoc/list.html", "list.html", "index.html"]
    """
    # Template suffixes for each page type
    suffixes = {
        "home": ["home.html", "index.html"],
        "list": ["list.html", "index.html"],
        "single": ["single.html", "page.html"],
    }

    # Add type-prefixed templates first
    candidates: list[str] = [f"{type_prefix}/{suffix}" for suffix in suffixes[page_type]]

    # Add extra prefix templates (e.g., autodoc/ for autodoc/python)
    if extra_prefixes:
        candidates.extend(
            f"{prefix}/{suffix}" for prefix in extra_prefixes for suffix in suffixes[page_type]
        )

    # Add generic fallbacks
    candidates.extend(suffixes[page_type])

    return candidates


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
