"""
Isolated (separate-heap) render backend for large cold builds — issue #350.

Renders a cold build's pages across separate-heap worker processes (fork +
copy-on-write today; a spawn re-derive fallback for non-fork platforms), which
recovers the in-process→separate-heap render-throughput gap that free-threaded
threads cannot (see ``benchmarks/render-scaling-attribution-findings.md``).

Selected behind a crossover gate (S5) and used for cold CLI/CI builds only —
never the dev server or incremental builds. The build's render phase is expected
to fall back to the in-process thread path if the isolated backend raises.

Public API:
- ``IsolatedRenderBackend`` — the driver (partition → fork → render → merge).
- ``partition_pages`` — deterministic parsed-page partitioner (S3).
- ``ContentFile`` / ``discover_content_files`` / ``partition_content_files`` —
  the pre-parse content sharder for the Phase-2 shard-parallel build (S12).
- ``fork_available`` — platform capability probe.
"""

from __future__ import annotations

from .backend import IsolatedRenderBackend, fork_available
from .gate import (
    IsolationDecision,
    IsolationSettings,
    decide_isolation,
    resolve_isolation_settings,
)
from .partition import (
    ContentFile,
    discover_content_files,
    estimate_file_cost,
    estimate_render_cost,
    partition_content_files,
    partition_pages,
)

__all__ = [
    "ContentFile",
    "IsolatedRenderBackend",
    "IsolationDecision",
    "IsolationSettings",
    "decide_isolation",
    "discover_content_files",
    "estimate_file_cost",
    "estimate_render_cost",
    "fork_available",
    "partition_content_files",
    "partition_pages",
    "resolve_isolation_settings",
]
