"""
Types for rebuild classification.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RebuildDecision:
    """Result of classifying whether a full rebuild is required."""

    full_rebuild: bool
    reason: str
