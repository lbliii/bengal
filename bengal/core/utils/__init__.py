"""
Core utilities for Bengal models.

This package provides shared utility functions used across the core domain
models (Page, Section, Site, Asset). Extracting common patterns into this
module reduces code duplication and ensures consistent behavior.

Modules:
    text: HTML stripping and text truncation utilities
    sorting: Weight-based sorting with consistent defaults
    config: Config access helpers for nested config structures
    url: URL building and baseurl application

Usage:
    from bengal.core.utils import strip_html, DEFAULT_WEIGHT, apply_baseurl
    from bengal.core.utils.text import truncate_at_sentence
    from bengal.core.utils.sorting import weight_sort_key

"""

from __future__ import annotations

from bengal.core.utils.config import get_config_section, get_site_value
from bengal.core.utils.sorting import DEFAULT_WEIGHT, sorted_by_weight, weight_sort_key
from bengal.core.utils.text import (
    normalize_whitespace,
    strip_html,
    strip_html_and_normalize,
    truncate_at_sentence,
    truncate_at_word,
)
from bengal.core.utils.url import apply_baseurl

__all__ = [
    # Sorting utilities
    "DEFAULT_WEIGHT",
    # URL utilities
    "apply_baseurl",
    "get_config_section",
    # Config utilities
    "get_site_value",
    "normalize_whitespace",
    "sorted_by_weight",
    # Text utilities
    "strip_html",
    "strip_html_and_normalize",
    "truncate_at_sentence",
    "truncate_at_word",
    "weight_sort_key",
]
