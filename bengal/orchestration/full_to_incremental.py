"""
Bridge helpers for transitioning from full builds to incremental runs.

⚠️  TEST UTILITIES ONLY
========================
These utilities are primarily used in tests to simulate incremental passes
without invoking the full BuildOrchestrator.

**Not for production use:**
- Writes placeholder output for test verification
- Skips full rendering pipeline
- Use BuildOrchestrator.run() for production incremental builds

**Primary consumers:**
- tests/integration/test_full_to_incremental_sequence.py
- Test scenarios validating incremental build flows
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.orchestration.incremental import IncrementalOrchestrator

if TYPE_CHECKING:
    from bengal.core.site import Site


def run_incremental_bridge(
    site: Site, change_type: str, changed_paths: Iterable[str | Path]
) -> None:
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
