"""
Template selection helpers for Renderer.

Extracted from renderer.py so the public Renderer facade can stay a coordinator.
Priority is unchanged: explicit frontmatter template, content-type strategy,
section auto-detection, then page.html / index.html.

Tests monkeypatch Renderer._template_exists; selection must call that method.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.core.section.utils import get_page_section
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import PageLike

logger = get_logger(__name__)


def template_exists(renderer: Any, template_name: str) -> bool:
    """Return True if the template engine can load ``template_name``."""
    try:
        renderer.template_engine.env.get_template(template_name)
        return True
    except Exception as e:
        logger.debug(
            "template_check_failed",
            template=template_name,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False


def get_template_name(renderer: Any, page: PageLike) -> str:
    """
    Determine which template to use for a page.

    Priority order:
    1. Explicit template in frontmatter (`template: doc.html`)
    2. Content type strategy (delegates to strategy.get_template())
    3. Section-based auto-detection (e.g., `docs.html`, `docs/single.html`)
    4. Default fallback (`page.html` or `index.html`)
    """
    # 1. Explicit template (highest priority)
    if "template" in page.metadata:
        return str(page.metadata["template"])

    # 2. Get content type strategy and delegate
    # IMPORTANT: Use page.type property (not metadata.get) to include cascade resolution
    # This ensures pages inherit template selection from parent sections via cascade
    page_type = page.type
    content_type = None

    page_section = get_page_section(page)
    if page_section and hasattr(page_section, "metadata"):
        content_type = page_section.metadata.get("content_type")

    # Determine which strategy to use
    from bengal.content_types.registry import (
        CONTENT_TYPE_REGISTRY,
        get_strategy,
        normalize_page_type_to_content_type,
    )

    # Normalize page type to content type (handles special cases like python-module)
    strategy_type = None
    if page_type:
        strategy_type = normalize_page_type_to_content_type(page_type)
    elif content_type and content_type in CONTENT_TYPE_REGISTRY:
        strategy_type = content_type

    if strategy_type:
        strategy = get_strategy(strategy_type)
        # Delegate to strategy
        template_name = strategy.get_template(page, renderer.template_engine)
        if template_name:
            return template_name

    # 3. Section-based auto-detection (fallback)
    is_section_index = page.source_path.stem == "_index"
    if page_section:
        section_name = page_section.name

        if is_section_index:
            # Try section index templates in order of specificity
            templates_to_try = [
                f"{section_name}/list.html",  # Section directory structure
                f"{section_name}/index.html",  # Alternative directory
                f"{section_name}-list.html",  # Flat with suffix
                f"{section_name}.html",  # Flat simple
            ]
        else:
            # Try section page templates in order of specificity
            templates_to_try = [
                f"{section_name}/single.html",  # Section directory structure
                f"{section_name}/page.html",  # Alternative directory
                f"{section_name}.html",  # Flat
            ]

        # Check if any template exists
        for template_name in templates_to_try:
            if renderer._template_exists(template_name):
                return template_name

    # 4. Simple default fallback (no type/kind complexity)
    if is_section_index:
        # Section index without custom template
        return "index.html"

    # Regular page - just use page.html
    return "page.html"
