"""
Custom Jinja2 tests for Bengal templates.

Tests are used with 'is' operator for cleaner conditionals:
  {% if page is draft %} vs {% if page.metadata.get('draft', False) %}

Available tests:
  - draft: Check if page is a draft
  - featured: Check if page has 'featured' tag
  - match: Check if value matches a regex pattern
  - outdated: Check if page is older than N days (default 90)
  - section: Check if object is a Section
  - translated: Check if page has translations
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.rendering.jinja_utils import has_value, safe_get

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """
    Register custom template tests with Jinja2 environment.

    Args:
        env: Jinja2 environment
        site: Site instance
    """
    env.tests.update(
        {
            "draft": test_draft,
            "featured": test_featured,
            "match": test_match,
            "outdated": test_outdated,
            "section": test_section,
            "translated": test_translated,
        }
    )


def test_draft(page: Any) -> bool:
    """
    Test if page is a draft.

    Usage:
        {% if page is draft %}
        {% if post is not draft %}

    Args:
        page: Page object to test

    Returns:
        True if page is marked as draft
    """
    metadata = safe_get(page, "metadata")
    if not has_value(metadata):
        return False
    return bool(metadata.get("draft", False))


def test_featured(page: Any) -> bool:
    """
    Test if page has 'featured' tag.

    Usage:
        {% if page is featured %}
        {% if article is not featured %}

    Args:
        page: Page object to test

    Returns:
        True if page has 'featured' in tags
    """
    tags = safe_get(page, "tags", [])
    if not has_value(tags):
        return False
    return "featured" in tags


def test_match(value: Any, pattern: str) -> bool:
    """
    Test if value matches a regex pattern.

    Usage:
        {% if page.source_path is match('.*_index.*') %}
        {% if filename is match('^test_') %}
        {% if value is not match('deprecated') %}

    Args:
        value: Value to test (will be converted to string)
        pattern: Regular expression pattern to match

    Returns:
        True if value matches the pattern
    """
    if value is None:
        return False
    return bool(re.search(pattern, str(value)))


def test_outdated(page: Any, days: int = 90) -> bool:
    """
    Test if page is older than N days.

    Usage:
        {% if page is outdated %}         # 90 days default
        {% if page is outdated(30) %}     # 30 days
        {% if page is not outdated(180) %} # Within 6 months

    Args:
        page: Page object to test
        days: Number of days threshold (default: 90)

    Returns:
        True if page.date is older than specified days
    """
    page_date = safe_get(page, "date")
    if not has_value(page_date):
        return False

    try:
        if not isinstance(page_date, datetime):
            return False
        age = (datetime.now() - page_date).days
        return bool(age > days)
    except (TypeError, AttributeError):
        return False


def test_section(obj: Any) -> bool:
    """
    Test if object is a Section.

    Usage:
        {% if page is section %}
        {% if obj is not section %}

    Args:
        obj: Object to test

    Returns:
        True if object is a Section instance
    """
    from bengal.core.section import Section

    return isinstance(obj, Section)


def test_translated(page: Any) -> bool:
    """
    Test if page has translations.

    Usage:
        {% if page is translated %}
        {% if page is not translated %}

    Args:
        page: Page object to test

    Returns:
        True if page has translations available
    """
    translations = safe_get(page, "translations")
    if not has_value(translations):
        return False
    return bool(translations)
