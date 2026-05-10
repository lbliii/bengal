"""Tests for DevServer live reload bug fixes.

RFC: template-bugs-live-reload-issues
- Content hash cache must be seeded after initial/validation build so first edit
  can use reactive path
- Serve-first: watcher must start after validation to avoid race
"""

from __future__ import annotations

import errno
import socket
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest

from bengal.assets.manifest import AssetManifest
from bengal.orchestration.build.options import BuildCompletionPolicy
from bengal.server.dev_server import DevServer
from bengal.utils.observability.profile import BuildProfile
from bengal.utils.stats_minimal import MinimalStats


class TestDevServerContentHashCacheSeeding:
    """Tests that DevServer seeds content hash cache after build (bug fix)."""

    @pytest.mark.bengal(testroot="test-basic")
    def test_build_first_seeds_content_hash_cache_before_watcher_start(
        self, site, tmp_path: Path
    ) -> None:
        """Build-first mode seeds cache so first edit can use reactive path.

        Bug: DevServer's initial build used site.build() directly, never
        calling seed_content_hash_cache. First user edit fell back to full
        build instead of reactive path.
        """
        mock_watcher = MagicMock()
        mock_build_trigger = MagicMock()

        with (
            patch.object(DevServer, "_check_stale_processes"),
            patch.object(DevServer, "_has_cached_output", return_value=False),
            patch.object(DevServer, "_prepare_dev_config", return_value=False),
            patch.object(DevServer, "_create_server") as mock_create,
            patch.object(DevServer, "_create_watcher") as mock_create_watcher,
            patch.object(DevServer, "_init_reload_controller"),
            patch.object(DevServer, "_start_background_completion_build") as mock_background,
            patch(
                "bengal.server.dev_server.PIDManager.get_pid_file", return_value=tmp_path / "pid"
            ),
            patch("bengal.server.dev_server.PIDManager.write_pid_file"),
            patch("bengal.server.dev_server.ResourceManager") as mock_rm_class,
        ):
            mock_create_watcher.return_value = (mock_watcher, mock_build_trigger)
            mock_backend = MagicMock()
            mock_backend.port = 5173
            mock_create.return_value = mock_backend

            # build-first calls backend.start() directly; raise to exit
            mock_backend.start.side_effect = KeyboardInterrupt

            # ResourceManager context manager
            mock_rm = MagicMock()
            mock_rm_class.return_value.__enter__ = MagicMock(return_value=mock_rm)
            mock_rm_class.return_value.__exit__ = MagicMock(return_value=False)

            server = DevServer(site, watch=True, auto_port=False)
            # DevServer catches KeyboardInterrupt and exits gracefully, so start() returns normally
            server.start()

            mock_build_trigger.seed_content_hash_cache.assert_called_once()
            call_args = mock_build_trigger.seed_content_hash_cache.call_args[0][0]
            assert call_args == list(site.pages), (
                "seed_content_hash_cache should be called with list(site.pages)"
            )
            mock_background.assert_called_once_with(
                ANY,
                watcher_runner=mock_watcher,
            )
            mock_watcher.start.assert_not_called()

    def test_background_completion_runs_complete_policy_then_starts_watcher(
        self, tmp_path: Path
    ) -> None:
        """Background completion should finish deferred work before watching edits."""
        site = MagicMock()
        site.root_path = tmp_path
        site.output_dir = tmp_path / "public"
        site.output_dir.mkdir()
        site.config = {}
        site.pages = []
        mock_watcher = MagicMock()
        stats = MinimalStats(total_pages=1, build_time_ms=10.0, incremental=True)

        server = DevServer(site, watch=False, auto_port=False)

        with (
            patch.object(server, "_run_build_via_executor", return_value=stats) as mock_build,
            patch.object(server, "_clear_html_cache_after_build"),
            patch.object(server, "_set_active_palette"),
            patch.object(server, "_init_reload_controller"),
            patch("bengal.server.dev_server.display_build_stats"),
        ):
            thread = server._start_background_completion_build(
                BuildProfile.WRITER,
                watcher_runner=mock_watcher,
            )
            thread.join(timeout=2)

        assert not thread.is_alive()
        build_opts = mock_build.call_args.args[0]
        assert build_opts.completion_policy is BuildCompletionPolicy.COMPLETE
        mock_watcher.start.assert_called_once()


class TestDevServerServeFirstWatcherOrder:
    """Tests that serve-first watcher starts after validation (bug fix)."""

    @pytest.mark.bengal(testroot="test-basic")
    def test_serve_first_watcher_starts_after_validation(self, site, build_site) -> None:
        """Watcher must start after validation to avoid concurrent build race.

        Bug: Watcher started before _run_validation_build. User edits during
        validation could trigger trigger_build while site.build() was running.
        """
        build_site(incremental=True)
        assert (site.output_dir / "index.html").exists(), "Need cached output"

        mock_watcher = MagicMock()
        mock_build_trigger = MagicMock()
        validation_called = []

        original_validation = DevServer._run_validation_build

        def tracked_validation(self: DevServer, profile: object, port: int) -> None:
            validation_called.append(1)
            original_validation(self, profile, port)

        with (
            patch.object(DevServer, "_check_stale_processes"),
            patch.object(DevServer, "_has_cached_output", return_value=True),
            patch.object(DevServer, "_prepare_dev_config", return_value=False),
            patch.object(DevServer, "_create_server") as mock_create,
            patch.object(DevServer, "_create_watcher") as mock_create_watcher,
            patch.object(DevServer, "_run_validation_build", tracked_validation),
            patch(
                "bengal.server.dev_server.PIDManager.get_pid_file", return_value=Path("/tmp/pid")
            ),
            patch("bengal.server.dev_server.PIDManager.write_pid_file"),
            patch("bengal.server.dev_server.ResourceManager") as mock_rm_class,
        ):
            mock_create_watcher.return_value = (mock_watcher, mock_build_trigger)
            mock_backend = MagicMock()
            mock_backend.port = 5173
            mock_create.return_value = mock_backend
            # serve-first runs backend.start() in a thread; return immediately
            mock_backend.start.return_value = None

            mock_rm = MagicMock()
            mock_rm_class.return_value.__enter__ = MagicMock(return_value=mock_rm)
            mock_rm_class.return_value.__exit__ = MagicMock(return_value=False)

            server = DevServer(site, watch=True, auto_port=False)
            server.start()

            assert validation_called, "Validation should have run"
            mock_watcher.start.assert_called_once()
            mock_build_trigger.seed_content_hash_cache.assert_called_once()


class TestDevServerCachedOutputIntegrity:
    """Tests that serve-first rejects incomplete cached asset trees."""

    @pytest.mark.bengal(testroot="test-basic")
    def test_rejects_cached_output_with_missing_manifest_output(self, site, build_site) -> None:
        """Serve-first should reject cache when manifest outputs are missing."""
        build_site(incremental=False)

        manifest = AssetManifest.load(site.output_dir / "asset-manifest.json")
        assert manifest is not None, "Build should create an asset manifest"
        assert manifest.entries, "Build should create an asset manifest"

        missing_output = next(iter(manifest.entries.values())).output_path
        missing_path = site.output_dir / missing_output
        assert missing_path.exists(), f"Expected manifest output to exist: {missing_output}"
        missing_path.unlink()

        server = DevServer(site, watch=False, auto_port=False)
        assert server._has_cached_output() is False


class TestDevServerPortDetection:
    """Port probing should match the address families Pounce may bind."""

    def test_localhost_port_probe_checks_ipv6_listener(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        site = MagicMock()
        site.root_path = tmp_path
        site.output_dir = tmp_path / "public"

        def fake_getaddrinfo(host: str, port: int, **_kwargs: object):
            assert host == "localhost"
            return [
                (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("::1", port, 0, 0)),
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", port)),
            ]

        class FakeSocket:
            def __init__(self, family: int, _socktype: int, _proto: int) -> None:
                self.family = family

            def __enter__(self):
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def bind(self, _sockaddr: object) -> None:
                if self.family == socket.AF_INET6:
                    raise OSError(errno.EADDRINUSE, "Address already in use")

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        monkeypatch.setattr(socket, "socket", FakeSocket)

        server = DevServer(site, host="localhost", watch=False, auto_port=False)

        assert server._is_port_available(5173) is False
