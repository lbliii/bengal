from __future__ import annotations

from typing import Protocol


class ProgressReporter(Protocol):
    """
    Contract for reporting build progress and user-facing messages.

    Implementations: CLI, server, noop (tests), rich, etc.
    """

    def add_phase(self, phase_id: str, label: str, total: int | None = None) -> None: ...

    def start_phase(self, phase_id: str) -> None: ...

    def update_phase(
        self, phase_id: str, current: int | None = None, current_item: str | None = None
    ) -> None: ...

    def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None: ...

    def log(self, message: str) -> None: ...


class NoopReporter:
    """Default reporter that does nothing (safe for tests and quiet modes)."""

    def add_phase(self, phase_id: str, label: str, total: int | None = None) -> None:
        return None

    def start_phase(self, phase_id: str) -> None:
        return None

    def update_phase(
        self, phase_id: str, current: int | None = None, current_item: str | None = None
    ) -> None:
        return None

    def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None:
        return None

    def log(self, message: str) -> None:
        return None
