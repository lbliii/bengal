"""
Custom template tests for Bengal.

Tests are used with 'is' operator for cleaner conditionals:
  {% if page is draft %} vs {% if page.metadata.get('draft', False) %}

Available tests:
  - draft: Check if page is a draft
  - featured: Check if page has 'featured' tag
  - match: Check if value matches a regex pattern
  - outdated: Check if page is older than N days (default 90)
  - section: Check if object is a Section
  - translated: Check if page has translations

Engine-Agnostic:
These tests work with any template engine that provides a tests interface
(Jinja2, Kida, or custom engines via the adapter layer).

"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

from bengal.rendering.jinja_utils import has_value, safe_get

if TYPE_CHECKING:
    from bengal.protocols import SiteLike, TemplateEnvironment


def register(env: TemplateEnvironment, site: SiteLike) -> None:
    """
    Register custom template tests with template environment.

    Args:
        env: Template environment (Jinja2, Kida, or any engine with tests interface)
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


def test_draft(page: object) -> bool:
    """
    Test if page is a draft.

    Usage:
        {% if page is draft %}
        {% if post is not draft %}

    Args:
        page: Page-like object to test (duck-typed via safe_get)

    Returns:
        True if page is marked as draft

    """
    metadata = safe_get(page, "metadata")
    if not has_value(metadata):
        return False
    return bool(metadata.get("draft", False))


def test_featured(page: object) -> bool:
    """
    Test if page has 'featured' tag.

    Usage:
        {% if page is featured %}
        {% if article is not featured %}

    Args:
        page: Page-like object to test (duck-typed via safe_get)

    Returns:
        True if page has 'featured' in tags

    """
    tags = safe_get(page, "tags", [])
    if not has_value(tags):
        return False
    return "featured" in tags


def test_match(value: object, pattern: str) -> bool:
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


def test_outdated(page: object, days: int = 90) -> bool:
    """
    Test if page is older than N days.

    Usage:
        {% if page is outdated %}         # 90 days default
        {% if page is outdated(30) %}     # 30 days
        {% if page is not outdated(180) %} # Within 6 months

    Args:
        page: Page-like object to test (duck-typed via safe_get)
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


def test_section(obj: object) -> bool:
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


def test_translated(page: object) -> bool:
    """
    Test if page has translations.

    Usage:
        {% if page is translated %}
        {% if page is not translated %}

    Args:
        page: Page-like object to test (duck-typed via safe_get)

    Returns:
        True if page has translations available

    """
    translations = safe_get(page, "translations")
    if not has_value(translations):
        return False
    return bool(translations)
