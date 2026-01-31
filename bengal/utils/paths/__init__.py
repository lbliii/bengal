"""
Path management utilities for Bengal.

This sub-package provides path resolution, URL normalization, and output
path computation utilities.

Modules:
    paths: Directory structure management (BengalPaths, LegacyBengalPaths)
    path_resolver: CWD-independent path resolution (PathResolver)
    url_normalization: URL path normalization and validation
    url_strategy: URL and output path computation

Example:
    >>> from bengal.utils.paths.paths import PathResolver, normalize_url, join_url_paths
    >>> resolver = PathResolver(site.root_path)
    >>> abs_path = resolver.resolve("content/post.md")
    >>> url = normalize_url("/api/bengal")

"""

from bengal.utils.paths.normalize import to_posix
from bengal.utils.paths.path_resolver import PathResolver, resolve_path
from bengal.utils.paths.paths import BengalPaths, LegacyBengalPaths
from bengal.utils.paths.url_normalization import (
    clean_md_path,
    join_url_paths,
    normalize_url,
    path_to_slug,
    split_url_path,
    validate_url,
)
from bengal.utils.paths.url_strategy import URLStrategy

__all__ = [
    "BengalPaths",
    "LegacyBengalPaths",
    "PathResolver",
    "URLStrategy",
    "clean_md_path",
    "join_url_paths",
    "normalize_url",
    "path_to_slug",
    "resolve_path",
    "split_url_path",
    "to_posix",
    "validate_url",
]
