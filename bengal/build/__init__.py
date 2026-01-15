"""
Incremental build domain logic.

This package owns change detection, dependency tracking, and provenance
for incremental builds. It intentionally contains no I/O orchestration
logic (see bengal.orchestration) and no cache storage logic (see bengal.cache).
"""

from __future__ import annotations

__all__ = ["contracts", "detectors", "pipeline", "provenance", "tracking"]
