"""Tests for thread-safe core diagnostics collection."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from bengal.core.diagnostics import DiagnosticEvent, DiagnosticsCollector

pytestmark = pytest.mark.parallel_unsafe


def test_diagnostics_collector_handles_concurrent_emit() -> None:
    collector = DiagnosticsCollector()

    def emit_one(index: int) -> None:
        collector.emit(DiagnosticEvent(level="warning", code="test", data={"index": index}))

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(emit_one, range(100)))

    events = collector.drain()

    assert len(events) == 100
    assert {event.data["index"] for event in events} == set(range(100))


def test_diagnostics_collector_drain_is_atomic() -> None:
    collector = DiagnosticsCollector()
    collector.emit(DiagnosticEvent(level="warning", code="before"))

    first = collector.drain()
    second = collector.drain()

    assert [event.code for event in first] == ["before"]
    assert second == []
