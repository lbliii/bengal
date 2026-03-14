"""Dev server E2E: serve → modify → verify output updates.

Covers live reload: start dev server, change content, assert rebuilt output.
Plan: plan-production-maturity.md Phase 0A

Note: This test starts a real dev server and may require running outside
sandbox (e.g. `pytest ... --runxfail` or CI with full permissions) if
file watchers or process operations are restricted.
"""

from __future__ import annotations

import subprocess
import sys
import time
import uuid
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

DEV_SERVER_PORT = 19999
POLL_INTERVAL = 0.3
MAX_WAIT_READY = 15
MAX_WAIT_REBUILD = 12


def _poll_until_ready(base_url: str) -> bool:
    """Poll until server responds or timeout."""
    deadline = time.monotonic() + MAX_WAIT_READY
    while time.monotonic() < deadline:
        try:
            r = httpx.get(base_url, timeout=2)
            if r.status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(POLL_INTERVAL)
    return False


def _poll_until_contains(base_url: str, needle: str) -> bool:
    """Poll until response contains needle or timeout."""
    deadline = time.monotonic() + MAX_WAIT_REBUILD
    while time.monotonic() < deadline:
        try:
            r = httpx.get(base_url, timeout=2)
            if r.status_code == 200 and needle in r.text:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(POLL_INTERVAL)
    return False


@pytest.mark.e2e
@pytest.mark.slow
def test_dev_server_rebuilds_on_content_change(
    e2e_site_dir: Callable[[str], Path],
) -> None:
    """Dev server: modify content, verify output updates after rebuild."""
    site_dir = e2e_site_dir("test-basic")

    index_md = site_dir / "content" / "index.md"
    assert index_md.exists(), "test-basic must have content/index.md"

    marker = f"e2e-reload-{uuid.uuid4().hex[:12]}"
    base_url = f"http://127.0.0.1:{DEV_SERVER_PORT}/"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "bengal",
            "serve",
            "--port",
            str(DEV_SERVER_PORT),
            "--no-open",
            "--no-auto-port",
        ],
        cwd=site_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        if not _poll_until_ready(base_url):
            stderr = proc.stderr.read() if proc.stderr else ""
            proc.terminate()
            proc.wait(timeout=5)
            pytest.fail(f"Server did not become ready in {MAX_WAIT_READY}s. stderr: {stderr}")

        initial = httpx.get(base_url, timeout=5)
        assert initial.status_code == 200
        assert marker not in initial.text

        original = index_md.read_text(encoding="utf-8")
        try:
            index_md.write_text(original + f"\n\n{marker}\n", encoding="utf-8")
            if not _poll_until_contains(base_url, marker):
                pytest.fail(
                    f"Rebuilt output did not contain marker '{marker}' within {MAX_WAIT_REBUILD}s"
                )
        finally:
            index_md.write_text(original, encoding="utf-8")
    finally:
        proc.terminate()
        proc.wait(timeout=10)
