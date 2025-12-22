"""
Bridge helpers for transitioning from full builds to incremental runs.

⚠️  TEST UTILITIES ONLY
========================
These utilities are used in tests to simulate incremental passes without
invoking the full BuildOrchestrator. They provide a minimal incremental
execution path for test verification.

Warning:
    Not for production use. These helpers:
    - Write placeholder output for test verification
    - Skip the full rendering pipeline
    - Do not produce valid HTML output

    For production incremental builds, use BuildOrchestrator.build() with
    incremental=True.

Primary Consumers:
    - tests/integration/test_full_to_incremental_sequence.py
    - Test scenarios validating incremental build flows

Functions:
    run_incremental_bridge
        Executes a minimal incremental pass for the given site and change type.
        Supports content, template, and config change types.

See Also:
    bengal.orchestration.build: Production build orchestration
    bengal.orchestration.incremental: Full incremental logic
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
    normalized: set[str] = {str(p) for p in changed_paths}
    orch.process(change_type, normalized)


__all__ = ["run_incremental_bridge"]
