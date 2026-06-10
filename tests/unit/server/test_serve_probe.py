"""Unit tests for the dev-server serve-ability smoke check (#398).

Covers asset selection from the manifest, the HTTP probe decision logic
(200 passes, 404 fails loudly, empty manifest falls back to index), and the
loud failure-message formatting that references #392 / pounce#74.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING

import pytest

from bengal.assets.manifest import select_smoke_probe_asset
from bengal.server.serve_probe import (
    ProbeResult,
    choose_probe_path,
    format_probe_failure,
    probe_serve_ability,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write_manifest(output_dir: Path, assets: dict[str, str], *, create_files: bool = True) -> None:
    """Write an asset-manifest.json (and optionally the referenced files)."""
    payload = {
        "version": 1,
        "generated_at": "2026-01-01T00:00:00Z",
        "assets": {logical: {"output_path": out} for logical, out in assets.items()},
    }
    (output_dir / "asset-manifest.json").write_text(json.dumps(payload), encoding="utf-8")
    if create_files:
        for out in assets.values():
            file_path = output_dir / out
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("/* asset */", encoding="utf-8")


class TestSelectSmokeProbeAsset:
    def test_prefers_css_entry(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            {
                "js/app.js": "assets/js/app.js",
                "css/style.css": "assets/css/style.css",
            },
        )
        assert select_smoke_probe_asset(tmp_path) == "/assets/css/style.css"

    def test_falls_back_to_any_on_disk_entry_when_no_css(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, {"js/app.js": "assets/js/app.js"})
        assert select_smoke_probe_asset(tmp_path) == "/assets/js/app.js"

    def test_skips_manifest_entries_missing_on_disk(self, tmp_path: Path) -> None:
        # CSS referenced but not written; JS present → JS chosen, not the absent CSS.
        _write_manifest(tmp_path, {"js/app.js": "assets/js/app.js"}, create_files=True)
        _write_manifest(
            tmp_path,
            {"js/app.js": "assets/js/app.js", "css/style.css": "assets/css/missing.css"},
            create_files=False,
        )
        # Re-create only the JS file (manifest now references a missing CSS).
        (tmp_path / "assets" / "js").mkdir(parents=True, exist_ok=True)
        (tmp_path / "assets" / "js" / "app.js").write_text("x", encoding="utf-8")
        assert select_smoke_probe_asset(tmp_path) == "/assets/js/app.js"

    def test_returns_none_when_no_manifest(self, tmp_path: Path) -> None:
        assert select_smoke_probe_asset(tmp_path) is None

    def test_returns_none_when_manifest_entries_all_missing(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, {"css/style.css": "assets/css/style.css"}, create_files=False)
        assert select_smoke_probe_asset(tmp_path) is None


class TestChooseProbePath:
    def test_uses_manifest_asset(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, {"css/style.css": "assets/css/style.css"})
        assert choose_probe_path(tmp_path) == "/assets/css/style.css"

    def test_falls_back_to_root_when_empty_manifest(self, tmp_path: Path) -> None:
        # Empty-manifest fallback: probe index.html at "/".
        assert choose_probe_path(tmp_path) == "/"


class _Handler(BaseHTTPRequestHandler):
    """Tiny HTTP server returning a configurable status for any GET."""

    status_code = 200

    def do_GET(self) -> None:
        self.send_response(type(self).status_code)
        self.send_header("Content-Type", "text/css")
        self.end_headers()
        self.wfile.write(b"/* ok */")

    def log_message(self, *_args: object) -> None:  # silence test server logging
        pass


class _LiveServer:
    """Context manager running a real HTTP server on an ephemeral port."""

    def __init__(self, status_code: int) -> None:
        self._status = status_code

    def __enter__(self) -> int:
        handler = type("_H", (_Handler,), {"status_code": self._status})
        self._httpd = HTTPServer(("127.0.0.1", 0), handler)
        self._port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self._port

    def __exit__(self, *_exc: object) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


class TestProbeServeAbility:
    def test_returns_ok_on_200(self, tmp_path: Path) -> None:
        with _LiveServer(200) as port:
            result = probe_serve_ability("127.0.0.1", port, tmp_path, attempts=3)
        assert result.ok is True
        assert result.status == 200

    def test_fails_loudly_on_404(self, tmp_path: Path) -> None:
        with _LiveServer(404) as port:
            result = probe_serve_ability("127.0.0.1", port, tmp_path, attempts=3)
        assert result.ok is False
        assert result.status == 404
        assert result.reason is not None
        assert "404" in result.reason

    def test_probes_manifest_asset_path(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, {"css/style.css": "assets/css/style.css"})
        with _LiveServer(200) as port:
            result = probe_serve_ability("127.0.0.1", port, tmp_path, attempts=3)
        assert result.probe_path == "/assets/css/style.css"

    def test_empty_manifest_falls_back_to_root(self, tmp_path: Path) -> None:
        with _LiveServer(200) as port:
            result = probe_serve_ability("127.0.0.1", port, tmp_path, attempts=3)
        assert result.probe_path == "/"

    def test_unreachable_server_reports_connection_failure(self, tmp_path: Path) -> None:
        # Nothing listening on this port: probe exhausts retries and reports cleanly.
        with _LiveServer(200) as port:
            pass  # server now shut down; reuse its (now-free) port number
        result = probe_serve_ability(
            "127.0.0.1", port, tmp_path, attempts=2, retry_interval=0.01, timeout=0.2
        )
        assert result.ok is False
        assert result.status is None
        assert result.reason is not None


class TestFormatProbeFailure:
    def test_mentions_paths_and_pounce_reference(self, tmp_path: Path) -> None:
        result = ProbeResult(
            ok=False,
            url="http://localhost:5173/assets/css/style.css",
            probe_path="/assets/css/style.css",
            status=404,
            reason="server returned HTTP 404 for a known asset",
        )
        serving = tmp_path / ".bengal" / "staging"
        staging = tmp_path / "public"
        message = format_probe_failure(result, serving_dir=serving, staging_dir=staging)
        assert "404" in message
        assert str(serving) in message
        assert str(staging) in message
        assert "pounce#74" in message
        assert "#392" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
