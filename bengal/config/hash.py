"""
Configuration hash utility for cache invalidation.

This module provides deterministic hashing of the resolved configuration state,
enabling automatic cache invalidation when any effective configuration changes.
The hash captures the *resolved* configuration, not raw file contents, ensuring
correctness across environment variables, profiles, and split config files.

Use Cases:
    - **Build cache validation**: Detect when configuration changes require
      a full rebuild rather than incremental updates.
    - **Cache key generation**: Include config hash in cache keys to ensure
      cache entries are invalidated when configuration changes.
    - **Configuration comparison**: Determine if two resolved configurations
      are functionally identical regardless of source file order.

Hash Characteristics:
    - **Deterministic**: Same configuration always produces same hash,
      regardless of dictionary key order or file loading order.
    - **Truncated SHA-256**: Returns first 16 characters (64 bits) for
      practical uniqueness while keeping identifiers manageable.
    - **Cross-platform**: Uses POSIX paths for consistent hashing across
      operating systems.
    - **Stable**: Excludes internal/runtime keys that don't affect build output.

Key Functions:
    compute_config_hash: Compute deterministic hash of configuration state.

Example:
    >>> from bengal.config.hash import compute_config_hash
    >>> config = {"title": "My Site", "baseurl": "/"}
    >>> hash1 = compute_config_hash(config)
    >>> len(hash1)
    16
    >>> config2 = {"baseurl": "/", "title": "My Site"}  # Same values, different order
    >>> compute_config_hash(config2) == hash1
    True

See Also:
    - :mod:`bengal.cache.build_cache`: Uses config_hash for cache validation.
    - :mod:`bengal.config.loader`: Produces the configuration dict to hash.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bengal.utils.hashing import hash_str

# Keys to exclude from hashing (internal/runtime-computed, don't affect build output)
EXCLUDED_KEYS = frozenset(
    {
        "_paths",  # Internal BengalPaths object
        "_config_hash",  # Self-reference (shouldn't be there, defensive)
        "_theme_obj",  # Runtime Theme object
        "_site",  # Site backreference
        "_cache",  # Cache reference
        "_tracker",  # Tracker reference
    }
)


def _json_default(obj: Any) -> str:
    """
    Handle non-JSON-serializable types for deterministic hashing.

    Converts Python types that aren't natively JSON-serializable into
    string representations suitable for consistent hashing.

    Supported Types:
        - ``Path``: Converted to POSIX path string for cross-platform consistency.
        - ``set``, ``frozenset``: Sorted and converted to string.
        - Objects with ``__dict__``: Dictionary representation as string.
        - Other types: ``str()`` fallback.

    Args:
        obj: Object to convert to a hashable string representation.

    Returns:
        String representation suitable for deterministic hashing.
    """
    if isinstance(obj, Path):
        # Use POSIX paths for cross-platform consistency
        return str(obj.as_posix())
    if isinstance(obj, (set, frozenset)):
        # Sort for deterministic output
        return str(sorted(str(item) for item in obj))
    if hasattr(obj, "__dict__"):
        # Handle dataclasses and custom objects
        return str(obj.__dict__)
    # Fallback for any other type
    return str(obj)


def _clean_config(d: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively remove excluded keys from config dict.

    Removes internal/runtime keys that shouldn't affect build output:
    - Keys in EXCLUDED_KEYS set
    - Keys starting with underscore (private/internal)

    Args:
        d: Configuration dictionary to clean

    Returns:
        Cleaned dictionary without excluded keys
    """
    result = {}
    for k, v in d.items():
        # Skip excluded keys and private keys
        if k in EXCLUDED_KEYS or k.startswith("_"):
            continue
        # Recursively clean nested dicts
        if isinstance(v, dict):
            result[k] = _clean_config(v)
        else:
            result[k] = v
    return result


def compute_config_hash(config: dict[str, Any]) -> str:
    """
    Compute deterministic SHA-256 hash of configuration state.

    The hash is computed from the *resolved* configuration dictionary,
    capturing all effective settings including:
    - Base configuration from config files
    - Environment variable overrides
    - Profile-specific settings
    - Merged split config files

    Excludes internal/runtime keys that don't affect build output.

    Algorithm:
        1. Remove excluded/internal keys (keys starting with '_')
        2. Recursively sort all dictionary keys (deterministic ordering)
        3. Serialize to JSON with custom handler for non-JSON types
        4. Compute SHA-256 hash
        5. Return first 16 characters (sufficient for uniqueness)

    Args:
        config: Resolved configuration dictionary

    Returns:
        16-character hex string (truncated SHA-256)

    Examples:
        >>> config1 = {"title": "My Site", "baseurl": "/"}
        >>> config2 = {"baseurl": "/", "title": "My Site"}  # Same values, different order
        >>> compute_config_hash(config1) == compute_config_hash(config2)
        True

        >>> config3 = {"title": "My Site", "baseurl": "/blog"}
        >>> compute_config_hash(config1) == compute_config_hash(config3)
        False

        >>> # Internal keys don't affect hash
        >>> config4 = {"title": "My Site", "baseurl": "/", "_paths": object()}
        >>> compute_config_hash(config1) == compute_config_hash(config4)
        True
    """
    # Clean config by removing internal/excluded keys
    stable_config = _clean_config(config)

    # Serialize with deterministic key ordering
    serialized = json.dumps(
        stable_config,
        sort_keys=True,
        default=_json_default,
        ensure_ascii=True,
        separators=(",", ":"),  # Compact output for consistent hashing
    )

    # Compute SHA-256 and truncate to 16 chars (64 bits - collision-resistant enough)
    return hash_str(serialized, truncate=16)
