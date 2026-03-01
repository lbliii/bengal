"""Unit tests for output_collector_diagnostics module."""

from bengal.orchestration.render.output_collector_diagnostics import (
    SOURCE_HINTS,
    OutputCollectorSource,
    diagnose_missing_output_collector,
)


def test_known_source_returns_that_source() -> None:
    """When known_source is passed, diagnostic uses it with matching hint."""
    diagnostic = diagnose_missing_output_collector(
        build_context=None,
        caller="test",
        worker_threads=4,
        known_source=OutputCollectorSource.STREAMING_FALLBACK,
    )
    assert diagnostic.source == OutputCollectorSource.STREAMING_FALLBACK
    assert diagnostic.source.value == "streaming_fallback"
    assert diagnostic.hint == SOURCE_HINTS[OutputCollectorSource.STREAMING_FALLBACK]
    assert diagnostic.caller == "test"
    assert diagnostic.worker_threads == 4


def test_build_context_none() -> None:
    """When build_context is None, returns build_context_none source."""
    diagnostic = diagnose_missing_output_collector(
        build_context=None,
        caller="_render_parallel",
        worker_threads=8,
    )
    assert diagnostic.source == OutputCollectorSource.BUILD_CONTEXT_NONE
    assert diagnostic.build_context_present is False
    assert diagnostic.hint == SOURCE_HINTS[OutputCollectorSource.BUILD_CONTEXT_NONE]


def test_collector_not_propagated() -> None:
    """When build_context exists but output_collector is None, returns collector_not_propagated."""
    ctx = type("Ctx", (), {"output_collector": None})()
    diagnostic = diagnose_missing_output_collector(
        build_context=ctx,
        caller="_render_parallel",
        worker_threads=4,
    )
    assert diagnostic.source == OutputCollectorSource.COLLECTOR_NOT_PROPAGATED
    assert diagnostic.build_context_present is True
    assert diagnostic.hint == SOURCE_HINTS[OutputCollectorSource.COLLECTOR_NOT_PROPAGATED]


def test_unknown_when_context_has_collector() -> None:
    """When build_context has output_collector, returns unknown (caller should not call)."""
    collector = object()
    ctx = type("Ctx", (), {"output_collector": collector})()
    diagnostic = diagnose_missing_output_collector(
        build_context=ctx,
        caller="_render_parallel",
        worker_threads=4,
    )
    assert diagnostic.source == OutputCollectorSource.UNKNOWN
    assert diagnostic.build_context_present is True
    assert diagnostic.hint == SOURCE_HINTS[OutputCollectorSource.UNKNOWN]


def test_to_log_context_keys() -> None:
    """to_log_context returns dict with required keys."""
    diagnostic = diagnose_missing_output_collector(
        build_context=None,
        caller="test",
        worker_threads=2,
    )
    ctx = diagnostic.to_log_context()
    assert set(ctx.keys()) == {
        "source",
        "caller",
        "build_context_present",
        "worker_threads",
        "hint",
    }
    assert ctx["source"] == "build_context_none"
    assert ctx["caller"] == "test"
    assert ctx["build_context_present"] is False
    assert ctx["worker_threads"] == 2
    assert isinstance(ctx["hint"], str)
    assert len(ctx["hint"]) > 0


def test_all_source_hints_exist() -> None:
    """Every OutputCollectorSource has a non-empty hint in SOURCE_HINTS."""
    for source in OutputCollectorSource:
        assert source in SOURCE_HINTS
        hint = SOURCE_HINTS[source]
        assert isinstance(hint, str)
        assert len(hint.strip()) > 0
