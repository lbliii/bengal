"""
Configuration hash utility for cache invalidation.

This module provides deterministic hashing of configuration state,
enabling automatic cache invalidation when the effective configuration
changes (including env vars, profiles, and split config files).

Architecture:
    The hash captures the *resolved* configuration state, not just file contents.
    This ensures cache correctness when:
    - Environment variables change (BENGAL_*)
    - Build profiles change (--profile writer)
    - Split config files change (config/environments/local.yaml)

Related:
    - bengal/cache/build_cache.py: Uses config_hash for validation
    - bengal/config/loader.py: Produces the config dict to hash
    - plan/active/rfc-zensical-inspired-patterns.md: Design rationale
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _json_default(obj: Any) -> str:
    """
    Handle non-JSON-serializable types for hashing.

    Converts Path, set, frozenset, and other types to strings
    for consistent serialization.

    Args:
        obj: Object to convert

    Returns:
        String representation suitable for hashing
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
    full_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return full_hash[:16]

