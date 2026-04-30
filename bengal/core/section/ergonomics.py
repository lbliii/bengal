"""Compatibility re-exports for Section template ergonomic helpers.

The implementation lives in :mod:`bengal.rendering.section_ergonomics` because
these helpers derive theme-facing content views and rendered content statistics.
This module remains for older internal imports that reached through
``bengal.core.section.ergonomics`` directly.
"""

from __future__ import annotations

from typing import Any


def content_pages(section: Any) -> list[Any]:
    from bengal.rendering.section_ergonomics import content_pages as _content_pages

    return _content_pages(section)


def recent_pages(section: Any, limit: int = 10) -> list[Any]:
    from bengal.rendering.section_ergonomics import recent_pages as _recent_pages

    return _recent_pages(section, limit)


def pages_with_tag(section: Any, tag: str) -> list[Any]:
    from bengal.rendering.section_ergonomics import pages_with_tag as _pages_with_tag

    return _pages_with_tag(section, tag)


def featured_posts(section: Any, limit: int = 5) -> list[Any]:
    from bengal.rendering.section_ergonomics import featured_posts as _featured_posts

    return _featured_posts(section, limit)


def post_count(section: Any) -> int:
    from bengal.rendering.section_ergonomics import post_count as _post_count

    return _post_count(section)


def post_count_recursive(section: Any) -> int:
    from bengal.rendering.section_ergonomics import post_count_recursive as _post_count_recursive

    return _post_count_recursive(section)


def word_count(section: Any) -> int:
    from bengal.rendering.section_ergonomics import word_count as _word_count

    return _word_count(section)


def total_reading_time(section: Any) -> int:
    from bengal.rendering.section_ergonomics import total_reading_time as _total_reading_time

    return _total_reading_time(section)


def aggregate_content(section: Any) -> dict[str, Any]:
    from bengal.rendering.section_ergonomics import aggregate_content as _aggregate_content

    return _aggregate_content(section)


def apply_section_template(section: Any, template_engine: Any) -> str:
    from bengal.rendering.section_ergonomics import (
        apply_section_template as _apply_section_template,
    )

    return _apply_section_template(section, template_engine)


__all__ = [
    "aggregate_content",
    "apply_section_template",
    "content_pages",
    "featured_posts",
    "pages_with_tag",
    "post_count",
    "post_count_recursive",
    "recent_pages",
    "total_reading_time",
    "word_count",
]
