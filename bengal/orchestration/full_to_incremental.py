"""
Bridge helpers for transitioning from full builds to incremental runs.

These utilities are primarily used in tests to simulate incremental passes
without invoking the full BuildOrchestrator.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from bengal.orchestration.incremental import IncrementalOrchestrator


def run_incremental_bridge(site, change_type: str, changed_paths: Iterable[str | Path]) -> None:
    """Run a minimal incremental pass for the given site.

    Args:
        site: Site instance
        change_type: One of "content", "template", or "config"
        changed_paths: Paths that changed (ignored for config)
    """
    orch = IncrementalOrchestrator(site)
    orch.initialize(enabled=True)
    normalized = {Path(p) for p in changed_paths}
    orch.process(change_type, normalized)


__all__ = ["run_incremental_bridge"]
