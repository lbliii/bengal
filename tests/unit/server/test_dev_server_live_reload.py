"""Tests for DevServer live reload bug fixes.

RFC: template-bugs-live-reload-issues
- Content hash cache must be seeded after initial/validation build so first edit
  can use reactive path
- Serve-first: watcher must start after validation to avoid race

RFC: rfc-dev-server-buffer-hardening (Phase 2)
- _has_cached_output requires assets/css for serve-first
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.server.dev_server import DevServer


class TestHasCachedOutputAssetCheck:
    """RFC: rfc-dev-server-buffer-hardening (Phase 2) - require CSS assets."""

    @pytest.mark.bengal(testroot="test-basic")
    def test_rejects_cache_without_css_assets(self, site, build_site, tmp_path: Path) -> None:
        """HTML + build cache but no assets/css → falls back to build-first."""
        build_site(incremental=True)
        # Remove assets to simulate rm -rf public/assets
        assets_dir = site.output_dir / "assets"
        if assets_dir.exists():
            import shutil

            shutil.rmtree(assets_dir)

        server = DevServer(site, watch=False, auto_port=False)
        assert server._has_cached_output() is False

    @pytest.mark.bengal(testroot="test-basic")
    def test_accepts_cache_with_css_assets(self, site, build_site) -> None:
        """Full build with assets/css → serve-first allowed."""
        build_site(incremental=True)
        assets_css = site.output_dir / "assets" / "css"
        assert assets_css.exists(), "test-basic build should produce assets/css"
        assert any(assets_css.iterdir()), "assets/css should have files"

        server = DevServer(site, watch=False, auto_port=False)
        assert server._has_cached_output() is True


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
