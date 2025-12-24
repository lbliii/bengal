"""Unit tests for cache version validation."""

import pickle
import sys

from bengal.cache.version import (
    CACHE_FORMAT_VERSION,
    CacheVersion,
    prepend_cache_header,
    validate_cache_header,
)


def test_cache_version_current():
    """Test CacheVersion.current() returns correct values."""
    version = CacheVersion.current()
    assert version.format_version == CACHE_FORMAT_VERSION
    assert version.python_major == sys.version_info[0]
    assert version.python_minor == sys.version_info[1]


def test_cache_version_is_compatible():
    """Test CacheVersion.is_compatible()."""
    version = CacheVersion.current()
    assert version.is_compatible() is True

    # Incompatible format version
    old_version = CacheVersion(CACHE_FORMAT_VERSION - 1, sys.version_info[0], sys.version_info[1])
    assert old_version.is_compatible() is False

    # Incompatible Python version
    other_python = CacheVersion(CACHE_FORMAT_VERSION, sys.version_info[0], sys.version_info[1] + 1)
    assert other_python.is_compatible() is False


def test_cache_magic_header_validation():
    """Test magic header validation."""
    data = b"test data"
    versioned = prepend_cache_header(data)

    is_valid, remaining = validate_cache_header(versioned)
    assert is_valid is True
    assert remaining == data


def test_invalid_header_rejected():
    """Test that invalid headers are rejected."""
    # Too short
    is_valid, remaining = validate_cache_header(b"bg")
    assert is_valid is False
    assert remaining == b"bg"

    # Wrong magic prefix
    is_valid, remaining = validate_cache_header(b"invalid header data")
    assert is_valid is False

    # Correct prefix, wrong version/python info
    wrong_magic = b"bg" + b"junkdata"
    is_valid, remaining = validate_cache_header(wrong_magic + b"more junk")
    assert is_valid is False


def test_old_version_header_rejected():
    """Simulates cache from previous Bengal version."""
    # Create header with different format version
    old_magic = (
        b"bg"
        + pickle.dumps(0, 2)
        + pickle.dumps((sys.version_info[0] << 24) | sys.version_info[1], 2)
    )
    old_cache = old_magic + b"stale data"

    is_valid, _ = validate_cache_header(old_cache)
    assert is_valid is False


