"""
Pagination utilities for splitting collections into pages.

This package provides generic pagination for content collections (pages, posts,
tags) with template-friendly context generation for navigation controls.

Components:
Paginator: Generic paginator with 1-indexed pages and navigation context

Example:
    >>> from bengal.utils.pagination import Paginator
    >>>
    >>> # Paginate blog posts
    >>> paginator = Paginator(posts, per_page=10)
    >>> first_page = paginator.page(1)
    >>>
    >>> # Get template context for navigation
    >>> ctx = paginator.page_context(page_number=2, base_url="/blog/")

Related:
- bengal/orchestration/section.py: Uses for section archives
- bengal/orchestration/taxonomy.py: Uses for tag pages
- bengal/rendering/template_functions/: Pagination filters

"""

from __future__ import annotations

from bengal.utils.pagination.paginator import Paginator

__all__ = ["Paginator"]
