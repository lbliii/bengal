"""Integration test conftest: SIGALRM hard timeout for CI.

pytest-timeout's thread method cannot interrupt C-extension calls or lock
acquisitions, so hung tests block the entire xdist worker until the CI job
timeout (25 min) kills the runner. SIGALRM is delivered by the OS and can
interrupt any blocking call.

Only active on Linux CI where SIGALRM is available and xdist workers run
tests in their main thread.
"""

from __future__ import annotations

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
        raise TimeoutError("SIGALRM: integration test exceeded 110s hard timeout")

    old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(110)  # 110s — fires before the 120s pytest-timeout
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
