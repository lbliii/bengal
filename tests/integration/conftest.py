"""Integration test conftest: SIGALRM hard timeout for CI.

pytest-timeout's thread method cannot interrupt C-extension calls or lock
acquisitions, so hung tests block the entire xdist worker until the CI job
timeout (25 min) kills the runner. SIGALRM is delivered by the OS and can
interrupt any blocking call.

Only active on Linux CI where SIGALRM is available and xdist workers run
tests in their main thread.

IMPORTANT: The SIGALRM handler must be minimal.  Under free-threaded Python
3.14t, ``faulthandler.dump_traceback(all_threads=True)`` can deadlock while
suspending threads, which prevents the ``raise TimeoutError`` from ever
executing.  We rely on ``faulthandler.dump_traceback_later`` (separate C
thread, best-effort) for diagnostics and keep the signal handler itself as
lightweight as possible.
"""

from __future__ import annotations

import faulthandler
import os
import signal
import sys

import pytest


@pytest.fixture(autouse=True)
def _hard_build_timeout():
    """SIGALRM hard timeout — kills tests even when thread timeout cannot."""
    if sys.platform != "linux" or not os.environ.get("CI"):
        yield
        return

    def _alarm_handler(signum, frame):
        # Keep this handler minimal — do NOT call faulthandler.dump_traceback()
        # here.  Under free-threaded Python 3.14t, dump_traceback(all_threads=True)
        # can deadlock when suspending threads, which prevents the raise below
        # from ever executing and hangs the entire xdist worker for 25 minutes.
        #
        # Diagnostics come from faulthandler.dump_traceback_later() set up below,
        # which runs in a separate C thread (best-effort, may also hang under ft).
        print(
            "\nSIGALRM: integration test exceeded 110s hard timeout",
            file=sys.stderr,
            flush=True,
        )
        raise TimeoutError("SIGALRM: integration test exceeded 110s hard timeout")

    old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    # Best-effort diagnostics: dump stacks at 105s from a separate C thread.
    # Under free-threaded Python this may also deadlock, but it fires 5s before
    # SIGALRM so in the common case we get stacks before the test is killed.
    faulthandler.dump_traceback_later(105, repeat=False, file=sys.stderr)
    signal.alarm(110)  # 110s — fires before the 120s pytest-timeout
    try:
        yield
    finally:
        signal.alarm(0)
        faulthandler.cancel_dump_traceback_later()
        signal.signal(signal.SIGALRM, old_handler)
