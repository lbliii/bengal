"""Integration test conftest: watchdog hard timeout for CI.

pytest-timeout's thread method cannot interrupt C-extension calls or lock
acquisitions, so hung tests block the entire xdist worker until the CI job
timeout (25 min) kills the runner.

Previous approaches using SIGALRM failed under free-threaded Python 3.14t:
- The signal is never delivered when the main thread is stuck in certain
  lock acquisitions or C-extension calls on the no-GIL build.
- Even when delivered, faulthandler.dump_traceback(all_threads=True)
  deadlocks while suspending threads.

The watchdog thread approach is more robust:
- threading.Event.wait() fires reliably regardless of main-thread state.
- os._exit() cannot be caught or blocked — it terminates the xdist worker.
- --max-worker-restart=3 in CI restarts the killed worker and marks the
  test as failed rather than hanging the entire shard for 25 minutes.
"""

from __future__ import annotations

import os
import sys
import threading

import pytest

# Hard timeout in seconds — must fire before the 120s pytest-timeout
# and well before the 25-minute CI job timeout.
_WATCHDOG_TIMEOUT = 110


@pytest.fixture(autouse=True)
def _hard_build_timeout():
    """Watchdog hard timeout — kills xdist worker when all else fails."""
    if sys.platform != "linux" or not os.environ.get("CI"):
        yield
        return

    done = threading.Event()

    def _watchdog():
        if not done.wait(_WATCHDOG_TIMEOUT):
            # Test exceeded hard timeout — dump what we can, then hard-exit.
            # os._exit() bypasses all cleanup, exception handlers, and finally
            # blocks.  The xdist coordinator sees the worker die and (with
            # --max-worker-restart) spins up a replacement.
            print(
                f"\nWATCHDOG: integration test exceeded {_WATCHDOG_TIMEOUT}s "
                f"hard timeout — killing xdist worker via os._exit(1)",
                file=sys.stderr,
                flush=True,
            )
            os._exit(1)

    t = threading.Thread(target=_watchdog, name="test-watchdog", daemon=True)
    t.start()
    try:
        yield
    finally:
        done.set()  # Cancel the watchdog — test finished normally
