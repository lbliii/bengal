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
    Protocol for reporting build progress and user-facing messages.

    Defines interface for progress reporting implementations. Used throughout
    the build system for consistent progress reporting across CLI, server, and
    test contexts.

    Creation:
        Protocol - not instantiated directly. Implementations include:
        - NoopReporter: No-op implementation for tests
        - LiveProgressReporterAdapter: Adapter for LiveProgressManager
        - CLI implementations: Rich progress bars for CLI

    Relationships:
        - Implemented by: NoopReporter, LiveProgressReporterAdapter, CLI reporters
        - Used by: BuildOrchestrator for build progress reporting
        - Used by: All orchestrators for phase progress updates

    Examples:
        # Protocol usage (type checking)
        def report_progress(reporter: ProgressReporter):
            reporter.start_phase("rendering")
            reporter.update_phase("rendering", current=5, total=10)
            reporter.complete_phase("rendering")
    """

    def add_phase(self, phase_id: str, label: str, total: int | None = None) -> None: ...

    def start_phase(self, phase_id: str) -> None: ...

    def update_phase(
        self, phase_id: str, current: int | None = None, current_item: str | None = None
    ) -> None: ...

    def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None: ...

    def log(self, message: str) -> None: ...


class NoopReporter:
    """
    No-op progress reporter implementation.

    Provides safe default implementation that does nothing, suitable for tests
    and quiet modes. All methods are no-ops that return immediately.

    Creation:
        Direct instantiation: NoopReporter()
            - Created as default reporter when no progress reporting needed
            - Safe for tests and quiet build modes

    Relationships:
        - Implements: ProgressReporter protocol
        - Used by: BuildOrchestrator as default reporter
        - Used in: Tests and quiet build modes

    Examples:
        reporter = NoopReporter()
        reporter.start_phase("rendering")  # No-op
        reporter.update_phase("rendering", current=5)  # No-op
    """

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
    """
    Adapter to bridge LiveProgressManager to ProgressReporter protocol.

    Provides adapter pattern implementation that bridges LiveProgressManager
    to the ProgressReporter protocol. Delegates phase methods directly and
    prints simple lines for log() messages.

    Creation:
        Direct instantiation: LiveProgressReporterAdapter(live_progress_manager)
            - Created by BuildOrchestrator when using LiveProgressManager
            - Requires LiveProgressManager instance

    Attributes:
        _pm: LiveProgressManager instance being adapted

    Relationships:
        - Implements: ProgressReporter protocol
        - Uses: LiveProgressManager for actual progress reporting
        - Used by: BuildOrchestrator for progress reporting

    Examples:
        adapter = LiveProgressReporterAdapter(live_progress_manager)
        adapter.start_phase("rendering")  # Delegates to _pm.start_phase()
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
        kwargs: dict[str, int | str] = {}
        if current is not None:
            kwargs["current"] = current
        if current_item is not None:
            kwargs["current_item"] = current_item
        self._pm.update_phase(phase_id, **kwargs)  # type: ignore[arg-type]

    def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None:
        self._pm.complete_phase(phase_id, elapsed_ms=elapsed_ms)

    def log(self, message: str) -> None:
        # Simple bridge: print; live manager handles phases only
        with suppress(Exception):
            print(message)
