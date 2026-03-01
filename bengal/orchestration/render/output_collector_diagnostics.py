"""
Structured diagnostics for output_collector propagation failures.

When hot reload tracking fails (output_collector missing in pipeline), this module
provides reason codes and hints so logs are actionable. Each failure mode maps
to a specific fix.

See: plan/output-collector-long-term-solution.md
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class OutputCollectorSource(Enum):
    """Reason code for why output_collector is missing."""

    STREAMING_FALLBACK = "streaming_fallback"
    RICH_PROGRESS_OMITTED = "rich_progress_omitted"
    BUILD_CONTEXT_NONE = "build_context_none"
    COLLECTOR_NOT_PROPAGATED = "collector_not_propagated"
    UNKNOWN = "unknown"


SOURCE_HINTS: dict[OutputCollectorSource, str] = {
    OutputCollectorSource.STREAMING_FALLBACK: (
        "StreamingRenderOrchestrator fallback dropped build_context. "
        "Pass build_context to orchestrator.process() in streaming.py fallback."
    ),
    OutputCollectorSource.RICH_PROGRESS_OMITTED: (
        "_render_parallel_with_progress omits output_collector. "
        "Pass output_collector explicitly to RenderingPipeline."
    ),
    OutputCollectorSource.BUILD_CONTEXT_NONE: (
        "process() called without build_context. "
        "Often caused by StreamingRenderOrchestrator fallback when KnowledgeGraph unavailable."
    ),
    OutputCollectorSource.COLLECTOR_NOT_PROPAGATED: (
        "build_context exists but output_collector is None. "
        "Fix phase_render caller to pass collector=output_collector."
    ),
    OutputCollectorSource.UNKNOWN: (
        "Hot reload will fall back to full reload. Run with BENGAL_LOG_LEVEL=debug for trace."
    ),
}


@dataclass(frozen=True)
class OutputCollectorDiagnostic:
    """Structured diagnostic for output_collector propagation failure."""

    source: OutputCollectorSource
    caller: str
    build_context_present: bool
    worker_threads: int
    hint: str

    def to_log_context(self) -> dict[str, Any]:
        """Convert to dict for logger.warning(**context)."""
        return {
            "source": self.source.value,
            "caller": self.caller,
            "build_context_present": self.build_context_present,
            "worker_threads": self.worker_threads,
            "hint": self.hint,
        }


def diagnose_missing_output_collector(
    *,
    build_context: Any,
    caller: str,
    worker_threads: int,
    known_source: OutputCollectorSource | None = None,
) -> OutputCollectorDiagnostic:
    """
    Determine why output_collector is missing and return structured diagnostic.

    Args:
        build_context: BuildContext passed to render (may be None)
        caller: Name of calling function for logs
        worker_threads: Number of worker threads affected
        known_source: If caller knows the reason (e.g. streaming fallback), pass it

    Returns:
        OutputCollectorDiagnostic with source, hint, and log context
    """
    if known_source is not None:
        return OutputCollectorDiagnostic(
            source=known_source,
            caller=caller,
            build_context_present=build_context is not None,
            worker_threads=worker_threads,
            hint=SOURCE_HINTS[known_source],
        )

    if build_context is None:
        return OutputCollectorDiagnostic(
            source=OutputCollectorSource.BUILD_CONTEXT_NONE,
            caller=caller,
            build_context_present=False,
            worker_threads=worker_threads,
            hint=SOURCE_HINTS[OutputCollectorSource.BUILD_CONTEXT_NONE],
        )

    if getattr(build_context, "output_collector", None) is None:
        return OutputCollectorDiagnostic(
            source=OutputCollectorSource.COLLECTOR_NOT_PROPAGATED,
            caller=caller,
            build_context_present=True,
            worker_threads=worker_threads,
            hint=SOURCE_HINTS[OutputCollectorSource.COLLECTOR_NOT_PROPAGATED],
        )

    return OutputCollectorDiagnostic(
        source=OutputCollectorSource.UNKNOWN,
        caller=caller,
        build_context_present=True,
        worker_threads=worker_threads,
        hint=SOURCE_HINTS[OutputCollectorSource.UNKNOWN],
    )
