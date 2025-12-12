"""
Core diagnostics events (no logging).

Core models must not log. Instead, they can optionally emit structured diagnostic
events to a sink/collector that orchestrators decide how to surface.
"""

from __future__ import annotations

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
