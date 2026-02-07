"""
Pure utility functions with no Bengal imports.

This sub-package contains foundation utilities that have zero dependencies
on other Bengal modules. They can be tested in isolation and are safe to
import from anywhere in the codebase without risk of circular dependencies.

Modules:
    hashing: Cryptographic hashing for cache keys and fingerprinting
    text: Text processing (slugify, truncate, HTML strip)
    dates: Date parsing, formatting, and time_ago
    types: Type introspection (Optional detection, type names)
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

from bengal.utils.primitives.code import (
    HL_LINES_PATTERN,
    parse_code_info,
    parse_hl_lines,
)
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
    slugify_id,
    strip_html,
    truncate_chars,
    truncate_middle,
    truncate_words,
    unescape_html,
)
from bengal.utils.primitives.types import (
    get_union_args,
    is_optional_type,
    is_union_type,
    type_display_name,
    unwrap_optional,
)

__all__ = [
    # code
    "HL_LINES_PATTERN",
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
    # types
    "get_union_args",
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
    # types
    "is_optional_type",
    "is_recent",
    # types
    "is_union_type",
    "iso_timestamp",
    "normalize_whitespace",
    "parse_code_info",
    "parse_date",
    "parse_hl_lines",
    "pluralize",
    # text
    "slugify",
    "slugify_id",
    "strip_html",
    "time_ago",
    "truncate_chars",
    "truncate_middle",
    "truncate_words",
    # types
    "type_display_name",
    "unescape_html",
    # types
    "unwrap_optional",
    "utc_now",
    "wrap_data",
]
