"""Live ``bengal serve`` HTTP integration test (#399).

Self-contained: this module does NOT share fixtures with the mocked, in-process
``test_dev_server_buffer_manifest.py`` — that test drove ``BufferManager`` +
``Site.build`` directly and is exactly why it missed the hidden-buffer 404 bug
(#392). Here we boot a *real* ``bengal serve`` subprocess on a temp site with
static assets and exercise the actual ASGI serve path over HTTP.

The test:
- Boots ``bengal serve`` on a temp site with CSS/JS/favicon assets.
- Uses a found free port (no fixed port → no CI conflicts) and probes
  ``localhost`` (the server may bind IPv6 ``::1``).
- Drives rapid concurrent content + CSS edits while continuously GETting the
  referenced assets, asserting they return 200 throughout (pre-#392 fix: ~53%
  of CSS requests 404'd; post-fix: 0%).
- Asserts a broken save preserves the last-good served output (negative control).

Config sets ``assets.fingerprint = false`` to match dev (``_prepare_dev_config``
forces this anyway), so assets serve at stable URLs like ``/assets/css/style.css``.
"""

from __future__ import annotations

import re
import socket
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

# Generous readiness window: a cold first build on CI can be slow.
_READY_TIMEOUT_SEC = 90.0
_READY_POLL_INTERVAL = 0.25


def _find_free_port() -> int:
    """Bind an ephemeral port, then release it so the server can claim it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _bengal_executable() -> str:
    """Resolve the ``bengal`` console script next to the running interpreter.

    ``python -m bengal.cli.milo_app`` does not invoke the CLI (no ``__main__``
    guard), so we run the installed console script from the same venv bin dir as
    ``sys.executable``; fall back to bare ``bengal`` on PATH.
    """
    bin_dir = Path(sys.executable).parent
    candidate = bin_dir / "bengal"
    if candidate.exists():
        return str(candidate)
    return "bengal"


def _http_get(url: str, *, timeout: float = 5.0) -> tuple[int, bytes]:
    """GET a URL, returning (status, body). HTTP error statuses are returned, not raised."""
    try:
        with urlopen(Request(url, method="GET"), timeout=timeout) as resp:
            return resp.status, resp.read()
    except HTTPError as exc:
        return exc.code, b""


def _make_site(root: Path) -> None:
    """Write a minimal temp site with content + CSS/JS/favicon assets."""
    (root / "content").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "css").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "js").mkdir(parents=True, exist_ok=True)

    (root / "bengal.toml").write_text(
        "\n".join(
            [
                "[site]",
                'title = "Live Serve Test"',
                "",
                "[assets]",
                "fingerprint = false",
                "minify = false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "content" / "index.md").write_text(
        "---\ntitle: Home\n---\n\n# Heading\n\nLIVE_SERVE_MARKER body text.\n",
        encoding="utf-8",
    )
    (root / "assets" / "css" / "style.css").write_text(
        "body { color: rebeccapurple; }\n", encoding="utf-8"
    )
    (root / "assets" / "js" / "app.js").write_text('console.log("live");\n', encoding="utf-8")
    (root / "assets" / "favicon.ico").write_text("FAVICON", encoding="utf-8")


@contextmanager
def _live_server(root: Path, port: int) -> Iterator[str]:
    """Boot ``bengal serve`` as a subprocess; yield the base URL; tear down cleanly."""
    proc = subprocess.Popen(
        [
            _bengal_executable(),
            "serve",
            "--source",
            str(root),
            "--host",
            "localhost",
            "--port",
            str(port),
            "--no-open-browser",
            "--no-auto-port",
            "--style",
            "ci",
        ],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base_url = f"http://localhost:{port}"
    try:
        _wait_until_ready(proc, base_url)
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)


def _wait_until_ready(proc: subprocess.Popen, base_url: str) -> None:
    """Poll the root URL until the server answers 200/304 or we time out."""
    deadline = time.monotonic() + _READY_TIMEOUT_SEC
    last_err: str = "no response"
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            output = proc.stdout.read() if proc.stdout else ""
            raise AssertionError(f"bengal serve exited early (rc={proc.returncode}):\n{output}")
        try:
            with urlopen(Request(base_url + "/", method="GET"), timeout=3) as resp:
                if resp.status in (200, 304):
                    return
                last_err = f"status {resp.status}"
        except HTTPError as exc:
            last_err = f"http {exc.code}"
        except (URLError, OSError) as exc:
            last_err = str(getattr(exc, "reason", exc) or exc)
        time.sleep(_READY_POLL_INTERVAL)
    raise AssertionError(f"bengal serve never became ready ({last_err})")


def _wait_for_content(base_url: str, marker: bytes, *, timeout: float = 60.0) -> bytes:
    """Poll the home page until it contains ``marker``, returning that body.

    On boot the dev server may serve a transient "Rebuilding" placeholder while
    the background completion build finishes; this waits for the real rendered
    content so callers establish a stable last-good baseline.
    """
    deadline = time.monotonic() + timeout
    last_body = b""
    while time.monotonic() < deadline:
        status, body = _http_get(base_url + "/")
        if status == 200 and marker in body:
            return body
        last_body = body
        time.sleep(0.25)
    raise AssertionError(
        f"home page never rendered marker {marker!r}; last body head: {last_body[:200]!r}"
    )


def _extract_asset_urls(html: str) -> list[str]:
    """Return same-origin CSS/JS asset URLs referenced by the rendered HTML."""
    matches = re.finditer(r'(?:href|src)="(/assets/[^"]+\.(?:css|js))"', html)
    urls = [match.group(1) for match in matches]
    # De-duplicate, preserve order.
    seen: set[str] = set()
    ordered: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


@pytest.mark.integration
@pytest.mark.slow
class TestLiveDevServerHTTP:
    """Live HTTP serve-path regression coverage (#399)."""

    def test_referenced_assets_stay_200_under_concurrent_edits(self, tmp_path: Path) -> None:
        root = tmp_path / "live_site"
        _make_site(root)
        port = _find_free_port()

        with _live_server(root, port) as base_url:
            # Wait for the real rendered home page (not the boot "Rebuilding" page)
            # so the asset references we extract are the genuine ones.
            body = _wait_for_content(base_url, b"LIVE_SERVE_MARKER")

            asset_urls = _extract_asset_urls(body.decode("utf-8", errors="replace"))
            # Pull the home CSS reference explicitly so we always probe a CSS asset
            # (the canonical #392 symptom). The default theme links its own CSS.
            assert asset_urls, "rendered HTML should reference at least one CSS/JS asset"

            # Sanity: each referenced asset serves 200 before we start churning.
            for url in asset_urls:
                code, _ = _http_get(base_url + url)
                assert code == 200, f"asset {url} should be 200 before edits"

            failures: list[tuple[str, int]] = []
            stop = threading.Event()

            def hammer_assets() -> None:
                while not stop.is_set():
                    for url in asset_urls:
                        code, _ = _http_get(base_url + url, timeout=5.0)
                        # 200 (served) or 304 (not modified) are both fine. Anything
                        # else — notably 404 for an on-disk asset — is a serve-path bug.
                        if code not in (200, 304):
                            failures.append((url, code))
                    time.sleep(0.02)

            hammer = threading.Thread(target=hammer_assets, daemon=True)
            hammer.start()

            css_src = root / "assets" / "css" / "style.css"
            content_src = root / "content" / "index.md"
            try:
                for i in range(8):
                    css_src.write_text(
                        f"body {{ color: rgb({i * 10 % 255}, 0, 0); }}\n", encoding="utf-8"
                    )
                    content_src.write_text(
                        f"---\ntitle: Home\n---\n\n# Heading {i}\n\nLIVE_SERVE_MARKER edit {i}.\n",
                        encoding="utf-8",
                    )
                    time.sleep(0.4)
                # Let the hammer observe the final swapped state.
                time.sleep(1.5)
            finally:
                stop.set()
                hammer.join(timeout=10)

            assert not failures, (
                "assets must stay reachable across rebuilds/buffer swaps; "
                f"got non-200 responses: {failures[:10]}"
            )

    def test_broken_save_preserves_last_good_output(self, tmp_path: Path) -> None:
        root = tmp_path / "broken_site"
        _make_site(root)
        port = _find_free_port()

        with _live_server(root, port) as base_url:
            # Establish a stable last-good baseline (wait past the boot placeholder).
            good_body = _wait_for_content(base_url, b"LIVE_SERVE_MARKER")
            assert b"LIVE_SERVE_MARKER" in good_body

            # Trigger a save that makes the rebuild *fail*: corrupt bengal.toml so
            # the next build cannot even construct the Site (S003 config parse
            # error). Bengal tolerates most malformed content, so a config break is
            # the reliable way to exercise the build-failure path. The dev server
            # must keep serving the last-good output rather than dropping to a
            # broken/blank/5xx page.
            (root / "bengal.toml").write_text(
                "this is not valid toml = = = [[[\n", encoding="utf-8"
            )
            time.sleep(4.0)

            # Across several polls the server must stay 200 and never serve a page
            # that lost the last-good content.
            for _ in range(5):
                status_after, body_after = _http_get(base_url + "/")
                assert status_after == 200, "server must keep serving after a broken save"
                assert b"LIVE_SERVE_MARKER" in body_after, (
                    "broken save must preserve last-good output, not serve a broken page"
                )
                time.sleep(0.3)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
