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
- bengal/protocols/infrastructure.py: ProgressReporter protocol definition
- NoopReporter: Test-friendly implementation in this module

"""

from __future__ import annotations

from contextlib import suppress
from typing import Any

# Import protocol from canonical location
from bengal.protocols import ProgressReporter

# Re-export for backwards compatibility
__all__ = ["ProgressReporter", "NoopReporter", "LiveProgressReporterAdapter"]


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
        self._pm.update_phase(phase_id, **kwargs)

    def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None:
        self._pm.complete_phase(phase_id, elapsed_ms=elapsed_ms)

    def log(self, message: str) -> None:
        # Simple bridge: print; live manager handles phases only
        with suppress(Exception):
            print(message)
