from __future__ import annotations

from bengal.orchestration.related_posts import compute_related


def related_posts(page, limit=3):
    """On-demand compute for template context."""
    if not hasattr(page, "related_posts") or not page.related_posts:
        page.related_posts = compute_related(page, limit=limit)
    return page.related_posts[:limit]
