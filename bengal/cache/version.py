"""Cache version management with magic header validation.

Adopted from Jinja2's bytecode cache pattern to ensure robust cache invalidation
across Python and Bengal version upgrades.
"""

from __future__ import annotations

import pickle
import sys
from typing import NamedTuple

# Increment when cache format changes
CACHE_FORMAT_VERSION = 1

# Magic bytes: "bg" + format version + Python version
# Uses pickle format 2 for compatibility and speed
CACHE_MAGIC = (
    b"bg"
    + pickle.dumps(CACHE_FORMAT_VERSION, 2)
    + pickle.dumps((sys.version_info[0] << 24) | sys.version_info[1], 2)
)


class CacheVersion(NamedTuple):
    """Parsed cache version info."""

    format_version: int
    python_major: int
    python_minor: int

    @classmethod
    def current(cls) -> CacheVersion:
        """Get the current environment's cache version info."""
        return cls(
            format_version=CACHE_FORMAT_VERSION,
            python_major=sys.version_info[0],
            python_minor=sys.version_info[1],
        )

    def is_compatible(self) -> bool:
        """Check if this version is compatible with current runtime."""
        current = self.current()
        return (
            self.format_version == current.format_version
            and self.python_major == current.python_major
            and self.python_minor == current.python_minor
        )


# CacheVersionError removed - use BengalCacheError with ErrorCode.A002 instead
# This class was deprecated in favor of the unified error system.


def validate_cache_header(data: bytes) -> tuple[bool, bytes]:
    """
    Validate cache magic header and return remaining data.

    Returns:
        Tuple of (is_valid, remaining_data). If invalid, returns (False, original_data).

    """
    if not data.startswith(b"bg"):
        return False, data

    if len(data) < len(CACHE_MAGIC):
        return False, data

    header = data[: len(CACHE_MAGIC)]
    if header != CACHE_MAGIC:
        return False, data

    return True, data[len(CACHE_MAGIC) :]


def prepend_cache_header(data: bytes) -> bytes:
    """Prepend magic header to cache data."""
    return CACHE_MAGIC + data
