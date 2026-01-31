"""
Centralized constants for Bengal analysis package.

This module defines default values for analysis thresholds and parameters
to ensure consistency across all analysis components.

"""

# Graph structure thresholds
DEFAULT_HUB_THRESHOLD: int = 10
"""Minimum incoming refs for a page to be considered a hub."""

DEFAULT_LEAF_THRESHOLD: int = 2
"""Maximum connectivity for a page to be considered a leaf."""
