"""
Test progress reporting utilities.

Provides progress feedback for long-running tests to improve visibility
during test execution. Uses pytest's capsys or prints directly to stderr.

Usage:
    def test_long_running(test_progress):
        with test_progress.phase("Processing items", total=100) as update:
            for i, item in enumerate(items):
                process(item)
                update(i + 1, item.name)  # Show progress

    # Or without context manager:
    def test_another(test_progress):
        test_progress.status("Starting heavy computation...")
        do_work()
        test_progress.status("Done!", done=True)
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class TestProgressReporter:
    """
    Progress reporter for long-running tests.

    Provides visual feedback during test execution without interfering
    with pytest's output capture. Respects verbosity settings.

    Attributes:
        verbose: Whether to print progress (default from pytest -v flag)
        prefix: Optional prefix for all messages (e.g., test name)
    """

    verbose: bool = True
    prefix: str = ""
    _start_times: dict[str, float] = field(default_factory=dict)

    def status(self, message: str, done: bool = False) -> None:
        """
        Print a status message.

        Args:
            message: Status message to display
            done: If True, indicates completion (adds checkmark)
        """
        if not self.verbose:
            return

        prefix = f"[{self.prefix}] " if self.prefix else ""
        indicator = "✓ " if done else "→ "
        print(f"  {indicator}{prefix}{message}", file=sys.stderr, flush=True)

    def step(self, step_num: int, total: int, description: str) -> None:
        """
        Print a step progress message.

        Args:
            step_num: Current step number (1-indexed)
            total: Total number of steps
            description: Description of current step
        """
        if not self.verbose:
            return

        prefix = f"[{self.prefix}] " if self.prefix else ""
        print(
            f"  → {prefix}Step {step_num}/{total}: {description}",
            file=sys.stderr,
            flush=True,
        )

    def iteration(
        self, current: int, total: int, item: str | None = None, every_n: int = 10
    ) -> None:
        """
        Print iteration progress (for loops).

        Args:
            current: Current iteration (1-indexed)
            total: Total iterations
            item: Optional current item name
            every_n: Only print every N iterations (default 10)
        """
        if not self.verbose:
            return

        # Only print at intervals or at end
        if current % every_n != 0 and current != total:
            return

        prefix = f"[{self.prefix}] " if self.prefix else ""
        pct = (current / total) * 100 if total > 0 else 0
        item_str = f" ({item})" if item else ""
        print(
            f"  → {prefix}{current}/{total} ({pct:.0f}%){item_str}",
            file=sys.stderr,
            flush=True,
        )

    @contextmanager
    def phase(
        self, name: str, total: int | None = None
    ) -> Iterator[Callable[[int | None, str | None], None]]:
        """
        Context manager for a timed phase with progress updates.

        Args:
            name: Phase name
            total: Total items (for percentage display)

        Yields:
            Update function: update(current, item_name) to report progress

        Example:
            with test_progress.phase("Processing pages", total=100) as update:
                for i, page in enumerate(pages):
                    process(page)
                    update(i + 1, page.name)
        """
        phase_id = name
        self._start_times[phase_id] = time.perf_counter()

        if self.verbose:
            prefix = f"[{self.prefix}] " if self.prefix else ""
            total_str = f" (0/{total})" if total else ""
            print(f"  ▶ {prefix}{name}{total_str}...", file=sys.stderr, flush=True)

        def update(current: int | None = None, item: str | None = None) -> None:
            """Update phase progress."""
            if not self.verbose or total is None:
                return
            if current is not None:
                pct = (current / total) * 100 if total > 0 else 0
                item_str = f" - {item}" if item else ""
                # Use carriage return to update in place
                print(
                    f"\r  ▶ {prefix}{name} ({current}/{total}, {pct:.0f}%){item_str}    ",
                    end="",
                    file=sys.stderr,
                    flush=True,
                )

        try:
            yield update
        finally:
            elapsed = time.perf_counter() - self._start_times.pop(phase_id, 0)
            if self.verbose:
                # Clear line and print completion
                print(
                    f"\r  ✓ {prefix}{name} completed in {elapsed:.2f}s    ",
                    file=sys.stderr,
                    flush=True,
                )

    @contextmanager
    def timed(self, description: str) -> Iterator[None]:
        """
        Simple timed context manager for operations.

        Args:
            description: Description of the operation

        Example:
            with test_progress.timed("Building site"):
                site.build()
        """
        if self.verbose:
            prefix = f"[{self.prefix}] " if self.prefix else ""
            print(f"  → {prefix}{description}...", file=sys.stderr, flush=True)

        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            if self.verbose:
                print(
                    f"  ✓ {prefix}{description} ({elapsed:.2f}s)",
                    file=sys.stderr,
                    flush=True,
                )


def create_test_progress(verbose: bool | None = None, prefix: str = "") -> TestProgressReporter:
    """
    Create a test progress reporter.

    Args:
        verbose: Override verbosity (None = auto-detect from pytest -v)
        prefix: Optional prefix for messages

    Returns:
        TestProgressReporter instance
    """
    if verbose is None:
        # Auto-detect from pytest verbose flag
        # Check if pytest is running in verbose mode
        import os

        verbose = os.environ.get("PYTEST_CURRENT_TEST") is not None and (
            "-v" in sys.argv or "--verbose" in sys.argv or "-vv" in sys.argv
        )

    return TestProgressReporter(verbose=verbose, prefix=prefix)


# Convenience function for quick status updates
def progress_status(message: str, done: bool = False) -> None:
    """
    Quick status message during tests (always prints to stderr).

    For long-running tests that need to show they're making progress.
    """
    indicator = "✓" if done else "→"
    print(f"  {indicator} {message}", file=sys.stderr, flush=True)


# Backward compatibility alias (deprecated, use progress_status instead)
def test_status(message: str, done: bool = False) -> None:
    """Deprecated: Use progress_status instead."""
    import warnings

    warnings.warn(
        "test_status is deprecated, use progress_status instead",
        DeprecationWarning,
        stacklevel=2,
    )
    progress_status(message, done)
