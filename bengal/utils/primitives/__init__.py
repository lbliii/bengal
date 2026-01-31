"""
Pure utility functions with no Bengal imports.

This sub-package contains foundation utilities that have zero dependencies
on other Bengal modules. They can be tested in isolation and are safe to
import from anywhere in the codebase without risk of circular dependencies.

Modules:
    hashing: Cryptographic hashing for cache keys and fingerprinting
    text: Text processing (slugify, truncate, HTML strip)
    dates: Date parsing, formatting, and time_ago
    sentinel: MISSING singleton for unambiguous missing states
    dotdict: Dictionary with dot notation access
    lru_cache: Thread-safe LRU cache with optional TTL

Example:
    >>> from bengal.utils.primitives import hash_str, slugify, MISSING, LRUCache
    >>> key = hash_str("content", truncate=8)
    >>> slug = slugify("Hello World!")
    >>> if value is MISSING:
    ...     value = default
    >>> cache = LRUCache(maxsize=100)

"""

from bengal.utils.primitives.dates import (
    DateLike,
    date_range_overlap,
    format_date_human,
    format_date_iso,
    format_date_rfc822,
    get_current_year,
    is_recent,
    iso_timestamp,
    parse_date,
    time_ago,
    utc_now,
)
from bengal.utils.primitives.dotdict import DotDict, wrap_data
from bengal.utils.primitives.hashing import (
    hash_bytes,
    hash_dict,
    hash_file,
    hash_file_with_stat,
    hash_str,
)
from bengal.utils.primitives.lru_cache import LRUCache
from bengal.utils.primitives.sentinel import MISSING, is_missing
from bengal.utils.primitives.text import (
    escape_html,
    format_path_for_display,
    generate_excerpt,
    humanize_bytes,
    humanize_number,
    humanize_slug,
    normalize_whitespace,
    pluralize,
    slugify,
    strip_html,
    truncate_chars,
    truncate_middle,
    truncate_words,
    unescape_html,
)

__all__ = [
    # sentinel
    "MISSING",
    # dates
    "DateLike",
    # dotdict
    "DotDict",
    # lru_cache
    "LRUCache",
    "date_range_overlap",
    "escape_html",
    "format_date_human",
    "format_date_iso",
    "format_date_rfc822",
    "format_path_for_display",
    "generate_excerpt",
    "get_current_year",
    "hash_bytes",
    "hash_dict",
    "hash_file",
    "hash_file_with_stat",
    # hashing
    "hash_str",
    "humanize_bytes",
    "humanize_number",
    "humanize_slug",
    "is_missing",
    "is_recent",
    "iso_timestamp",
    "normalize_whitespace",
    "parse_date",
    "pluralize",
    # text
    "slugify",
    "strip_html",
    "time_ago",
    "truncate_chars",
    "truncate_middle",
    "truncate_words",
    "unescape_html",
    "utc_now",
    "wrap_data",
]
