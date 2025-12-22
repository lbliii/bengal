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


def compute_config_hash(config: dict[str, Any]) -> str:
    """
    Compute deterministic SHA-256 hash of configuration state.

    The hash is computed from the *resolved* configuration dictionary,
    capturing all effective settings including:
    - Base configuration from config files
    - Environment variable overrides
    - Profile-specific settings
    - Merged split config files

    Algorithm:
        1. Recursively sort all dictionary keys (deterministic ordering)
        2. Serialize to JSON with custom handler for non-JSON types
        3. Compute SHA-256 hash
        4. Return first 16 characters (sufficient for uniqueness)

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
    """
    # Serialize with deterministic key ordering
    serialized = json.dumps(
        config,
        sort_keys=True,
        default=_json_default,
        ensure_ascii=True,
        separators=(",", ":"),  # Compact output for consistent hashing
    )

    # Compute SHA-256 and truncate to 16 chars (64 bits - collision-resistant enough)
    return hash_str(serialized, truncate=16)
