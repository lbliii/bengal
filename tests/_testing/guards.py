"""
Guard fixtures for Bengal tests.

Provides:
- process_guard: Automatically kills any new child processes created during a test.
- memory_guard: Monitors memory usage and fails if it exceeds a limit.
"""

import contextlib
import threading
import time

import pytest

try:
    import psutil
except ImportError:
    psutil = None


@pytest.fixture
def process_guard(request):
    """
    Guard against leaked processes.
    Ensures all child processes created during the test are terminated on teardown.

    This is an opt-in fixture. Use it by:
    1. Adding the fixture as a test parameter: def test_foo(process_guard): ...
    2. Using the marker: @pytest.mark.process_guard

    """
    # Check if activated via marker (allows using marker instead of fixture param)
    marker = request.node.get_closest_marker("process_guard")
    if marker is None and "process_guard" not in request.fixturenames:
        yield
        return

    if psutil is None:
        yield
        return

    # Track children before test
    try:
        process = psutil.Process()
        children_before = set(process.children(recursive=True))
    except (psutil.NoSuchProcess, Exception):
        yield
        return

    yield

    # Cleanup children after test
    try:
        children_after = set(process.children(recursive=True))
        leaked = children_after - children_before
        if leaked:
            # Give them a moment to exit naturally
            time.sleep(0.1)
            try:
                children_after = set(process.children(recursive=True))
                leaked = children_after - children_before
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                pass

            if leaked:
                # Sort by creation time (descending) to kill children before parents
                to_kill = []
                for child in leaked:
                    with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                        to_kill.append((child, child.create_time()))

                to_kill.sort(key=lambda x: x[1], reverse=True)

                for child, _ in to_kill:
                    try:
                        if child.is_running():
                            child.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
    except (psutil.NoSuchProcess, Exception):
        pass


@pytest.fixture(autouse=True)
def memory_guard(request):
    """Monitor memory usage for memory_intensive tests."""
    marker = request.node.get_closest_marker("memory_intensive")
    if not marker or psutil is None:
        yield
        return

    process = psutil.Process()
    # Default limit 2GB
    limit_gb = marker.kwargs.get("limit_gb", 2.0)
    max_memory = limit_gb * 1024 * 1024 * 1024
    stop_event = threading.Event()
    peak_memory = [0.0]

    def monitor():
        while not stop_event.is_set():
            try:
                mem = process.memory_info().rss
                # Also check recursive children memory
                for child in process.children(recursive=True):
                    with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                        mem += child.memory_info().rss

                if mem > peak_memory[0]:
                    peak_memory[0] = mem
                time.sleep(0.2)
            except (psutil.NoSuchProcess, Exception):
                break

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()

    try:
        yield
    finally:
        stop_event.set()
        monitor_thread.join(timeout=1.0)

        if peak_memory[0] > max_memory:
            peak_mb = peak_memory[0] / (1024 * 1024)
            limit_mb = max_memory / (1024 * 1024)
            pytest.fail(f"Memory limit exceeded: {peak_mb:.1f}MB (limit: {limit_mb:.1f}MB)")
