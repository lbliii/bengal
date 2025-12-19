"""
Utility functions and classes for Bengal SSG.
"""

from __future__ import annotations

from bengal.utils import (
    async_compat,
    dates,
    file_io,
    hashing,
    json_compat,
    retry,
    text,
    thread_local,
)
from bengal.utils.async_compat import run_async
from bengal.utils.hashing import hash_bytes, hash_dict, hash_file, hash_file_with_stat, hash_str
from bengal.utils.pagination import Paginator
from bengal.utils.path_resolver import PathResolver, resolve_path
from bengal.utils.paths import BengalPaths
from bengal.utils.retry import async_retry_with_backoff, calculate_backoff, retry_with_backoff
from bengal.utils.sections import resolve_page_section_path
from bengal.utils.text import humanize_slug
from bengal.utils.thread_local import ThreadLocalCache, ThreadSafeSet

__all__ = [
    "BengalPaths",
    "Paginator",
    "PathResolver",
    "ThreadLocalCache",
    "ThreadSafeSet",
    "async_compat",
    "async_retry_with_backoff",
    "calculate_backoff",
    "dates",
    "file_io",
    "hash_bytes",
    "hash_dict",
    "hash_file",
    "hash_file_with_stat",
    "hash_str",
    "hashing",
    "humanize_slug",
    "json_compat",
    "resolve_path",
    "resolve_page_section_path",
    "retry",
    "retry_with_backoff",
    "run_async",
    "text",
    "thread_local",
]
