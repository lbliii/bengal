"""
Progress reporting system for build progress tracking.

Provides protocol-based progress reporting with multiple implementations
(CLI, server, noop for tests). Enables consistent progress reporting across
different execution contexts.

Key Concepts:
    - Progress protocol: Protocol-based interface for progress reporting
    - Phase tracking: Build phase tracking with progress updates
    - Multiple implementations: CLI, server, noop, rich reporters
    - Adapter pattern: LiveProgressManager adapter for compatibility

Related Modules:
    - bengal.utils.live_progress: Live progress manager implementation
    - bengal.orchestration.build: Build orchestration using progress reporting
    - bengal.cli.commands.build: CLI build command using progress reporting

See Also:
    - bengal/utils/progress.py:ProgressReporter for progress protocol
    - bengal/utils/progress.py:NoopReporter for test-friendly implementation
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any, Protocol


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


class LiveProgressReporterAdapter:
    """Adapter to bridge LiveProgressManager to ProgressReporter.

    Delegates phase methods directly and prints simple lines for log().
    """

    def __init__(self, live_progress_manager: Any):
        self._pm = live_progress_manager

    def add_phase(self, phase_id: str, label: str, total: int | None = None) -> None:
        self._pm.add_phase(phase_id, label, total)

    def start_phase(self, phase_id: str) -> None:
        self._pm.start_phase(phase_id)

    def update_phase(
        self, phase_id: str, current: int | None = None, current_item: str | None = None
    ) -> None:
        if current is None and current_item is None:
            # Nothing to update
            return
        kwargs = {}
        if current is not None:
            kwargs["current"] = current
        if current_item is not None:
            kwargs["current_item"] = current_item
        self._pm.update_phase(phase_id, **kwargs)

    def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None:
        self._pm.complete_phase(phase_id, elapsed_ms=elapsed_ms)

    def log(self, message: str) -> None:
        # Simple bridge: print; live manager handles phases only
        with suppress(Exception):
            print(message)
