"""
Core diagnostics system for structured event emission.

Core models must not log directly. Instead, they emit structured diagnostic
events to a sink/collector that orchestrators decide how to surface. This
ensures core models remain pure data containers without side effects.

Public API:
    DiagnosticEvent: Structured event with level, code, and data dict
    DiagnosticsSink: Protocol for event receivers (implement .emit())
    DiagnosticsCollector: In-memory collector for build diagnostics
    emit: Convenience wrapper to emit events with kwargs
    emit_best_effort: Low-level emission with sink resolution

Key Concepts:
    Structured Events: DiagnosticEvent contains level (debug/info/warning/error),
        a machine-readable code, and arbitrary data dict.

    Sink Resolution: Events routed to sink via resolution order:
        1. obj._diagnostics (explicit injection)
        2. obj.diagnostics (e.g., Site.diagnostics)
        3. obj._site.diagnostics (common for linked models)

    Best-Effort: Diagnostics never affect core behavior. If sink is None
        or emission fails, events are silently dropped.

Usage:
    from bengal.core.diagnostics import emit

    # In a core model method:
    emit(self, "warning", "missing_title", page=page_path)

    # In an orchestrator (consuming events):
    collector = DiagnosticsCollector()
    site.diagnostics = collector
    # ... run build ...
    for event in collector.drain():
        if event.level == "error":
            logger.error(f"{event.code}: {event.data}")

Related Packages:
    bengal.core.site: Site can hold a diagnostics sink
    bengal.core.section: Sections emit diagnostics for collisions
    bengal.orchestration: Orchestrators configure and consume diagnostics
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

type DiagnosticLevel = Literal["debug", "info", "warning", "error"]


@dataclass(frozen=True)
class DiagnosticEvent:
    """A structured diagnostic emitted by core models."""

    level: DiagnosticLevel
    code: str
    data: dict[str, Any] = field(default_factory=dict)


class DiagnosticsSink(Protocol):
    """Sink interface for receiving diagnostics from core models."""

    def emit(self, event: DiagnosticEvent) -> None: ...


class DiagnosticsCollector:
    """In-memory collector for diagnostics emitted during a build."""

    def __init__(self) -> None:
        self._events: list[DiagnosticEvent] = []

    def emit(self, event: DiagnosticEvent) -> None:
        self._events.append(event)

    def drain(self) -> list[DiagnosticEvent]:
        events = list(self._events)
        self._events.clear()
        return events


def emit_best_effort(obj: Any | None, event: DiagnosticEvent) -> None:
    """
    Emit a diagnostic event if a sink is available.

    This is intentionally best-effort: diagnostics must never affect core behavior.

    Resolution order:
      1) obj._diagnostics (explicit injection on some core types)
      2) obj.diagnostics (e.g., Site.diagnostics attached by orchestrators)
      3) obj._site.diagnostics (common pattern for core models linked to a Site)
    """
    if obj is None:
        return

    sink: Any | None = getattr(obj, "_diagnostics", None)
    if sink is None:
        sink = getattr(obj, "diagnostics", None)
    if sink is None:
        site = getattr(obj, "_site", None)
        sink = getattr(site, "diagnostics", None) if site is not None else None

    if sink is None:
        return

    with contextlib.suppress(Exception):
        sink.emit(event)


def emit(obj: Any | None, level: DiagnosticLevel, code: str, **data: Any) -> None:
    """Convenience wrapper to emit a DiagnosticEvent."""
    emit_best_effort(obj, DiagnosticEvent(level=level, code=code, data=data))
