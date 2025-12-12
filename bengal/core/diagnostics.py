"""
Core diagnostics events (no logging).

Core models must not log. Instead, they can optionally emit structured diagnostic
events to a sink/collector that orchestrators decide how to surface.
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
