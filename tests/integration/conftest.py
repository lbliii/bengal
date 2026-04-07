"""Integration test conftest: external watchdog process for CI test timeouts.

pytest-timeout's thread method cannot interrupt C-extension calls or lock
acquisitions under free-threaded Python 3.14t, so hung tests block the
entire xdist worker until the CI job timeout (25 min) kills the runner.

Previous approaches all failed under free-threaded Python 3.14t:
- SIGALRM: never delivered when main thread stuck in lock acquisitions.
- In-process watchdog thread: also hangs (threading.Event.wait never fires
  when the process is stuck in an uninterruptible futex or C-level deadlock).

The external watchdog process approach is the nuclear option:
- A separate OS process sleeps for N seconds then sends SIGKILL to the
  test worker.  SIGKILL cannot be caught, blocked, or ignored.
- Uses pytest_runtest_setup hook (not a fixture) so the watchdog is armed
  BEFORE any fixture setup — catching hangs in class/session fixtures too.
- --max-worker-restart=3 in CI restarts the killed worker and marks the
  test as failed rather than hanging the entire shard for 25 minutes.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

# Hard timeout in seconds — must fire before the 120s pytest-timeout
# and well before the 25-minute CI job timeout.
_WATCHDOG_TIMEOUT = 110

# Track the watchdog subprocess per-test
_watchdog_proc: subprocess.Popen | None = None


def _start_watchdog() -> subprocess.Popen | None:
    """Spawn an external process that SIGKILLs us after _WATCHDOG_TIMEOUT seconds."""
    pid = os.getpid()
    # Use a shell one-liner: sleep, then kill.  The sleep is a kernel timer
    # so it fires even if the parent process is completely deadlocked.
    # SIGKILL (9) cannot be caught, blocked, or ignored.
    proc = subprocess.Popen(
        ["bash", "-c", f"sleep {_WATCHDOG_TIMEOUT} && kill -9 {pid}"],
        # Detach from parent's stdio to avoid pipe issues
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        # Start new process group so it doesn't get signals meant for us
        preexec_fn=os.setpgrp,
    )
    return proc


def _stop_watchdog(proc: subprocess.Popen | None) -> None:
    """Kill the watchdog process — test finished normally."""
    if proc is None:
        return
    try:
        proc.kill()  # SIGKILL the watchdog itself
        proc.wait(timeout=1)
    except ProcessLookupError, OSError, subprocess.TimeoutExpired:
        pass


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Hook: arm the watchdog BEFORE any fixture setup."""
    global _watchdog_proc
    if sys.platform != "linux" or not os.environ.get("CI"):
        return
    _watchdog_proc = _start_watchdog()


def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> None:
    """Hook: disarm the watchdog after the test (including fixture teardown)."""
    global _watchdog_proc
    _stop_watchdog(_watchdog_proc)
    _watchdog_proc = None


def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    """If setup or call phase fails, disarm the watchdog early."""
    global _watchdog_proc
    if call.excinfo is not None and call.when in ("setup", "call"):
        _stop_watchdog(_watchdog_proc)
        _watchdog_proc = None
