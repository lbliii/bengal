"""Tests for BuildTrigger rebuild plan."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.server.build_trigger import BuildTrigger


class TestDoubleBuffer:
    """Unit tests for the _DoubleBuffer prepare/swap/resync context manager.

    These cover the dev-server double-buffer invariant in isolation: the
    success-swap path, both exception-resync branches (swapped vs not), the
    #315 ``asset-manifest.json`` always-sync, and the no-buffer-manager no-op.
    """

    @pytest.fixture
    def site(self) -> MagicMock:
        site = MagicMock()
        site.output_dir = Path("/active")
        return site

    def _make_buffer_manager(self, tmp_path: Path) -> object:
        """Real BufferManager seeded with two on-disk buffers."""
        from bengal.server.buffer_manager import BufferManager

        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        return BufferManager(dir_a=dir_a, dir_b=dir_b)

    def test_no_buffer_manager_is_noop(self, site: MagicMock) -> None:
        """With no BufferManager, output_dir is left untouched on success."""
        from bengal.server.build_trigger import _DoubleBuffer

        original = site.output_dir
        with _DoubleBuffer(site, None, use_incremental=False, last_delta_paths=None) as buf:
            buf.swap()
        assert site.output_dir == original
        assert buf.swapped is False

    def test_no_buffer_manager_noop_on_exception(self, site: MagicMock) -> None:
        """With no BufferManager, output_dir is untouched even on error."""
        from bengal.server.build_trigger import _DoubleBuffer

        original = site.output_dir
        with (
            pytest.raises(RuntimeError),
            _DoubleBuffer(site, None, use_incremental=False, last_delta_paths=None),
        ):
            raise RuntimeError("boom")
        assert site.output_dir == original

    def test_enter_redirects_to_staging(self, site: MagicMock, tmp_path: Path) -> None:
        """__enter__ points output_dir at the staging buffer (full prep)."""
        from bengal.server.build_trigger import _DoubleBuffer

        mgr = self._make_buffer_manager(tmp_path)
        site.output_dir = mgr.active_dir
        with _DoubleBuffer(site, mgr, use_incremental=False, last_delta_paths=None):
            assert site.output_dir == mgr.staging_dir

    def test_success_swap_points_output_at_new_active(
        self, site: MagicMock, tmp_path: Path
    ) -> None:
        """On swap(), output_dir follows the now-active buffer; gen increments."""
        from bengal.server.build_trigger import _DoubleBuffer

        mgr = self._make_buffer_manager(tmp_path)
        site.output_dir = mgr.active_dir
        staging_before = mgr.staging_dir
        with _DoubleBuffer(site, mgr, use_incremental=False, last_delta_paths=None) as buf:
            buf.swap()
            assert buf.swapped is True
        # After swap, the old staging is now active and output_dir tracks it.
        assert mgr.active_dir == staging_before
        assert site.output_dir == staging_before
        assert mgr.generation == 1

    def test_exception_after_swap_keeps_output_on_new_active(
        self, site: MagicMock, tmp_path: Path
    ) -> None:
        """If swap ran then code fails, output_dir stays on the NEW active buffer."""
        from bengal.server.build_trigger import _DoubleBuffer

        mgr = self._make_buffer_manager(tmp_path)
        site.output_dir = mgr.active_dir
        staging_before = mgr.staging_dir
        with (  # noqa: PT012 - the swap() before raise is the behavior under test
            pytest.raises(RuntimeError),
            _DoubleBuffer(site, mgr, use_incremental=False, last_delta_paths=None) as buf,
        ):
            buf.swap()
            raise RuntimeError("post-swap failure")
        assert mgr.active_dir == staging_before
        assert site.output_dir == staging_before

    def test_exception_before_swap_reverts_to_original(
        self, site: MagicMock, tmp_path: Path
    ) -> None:
        """If swap has NOT run and the build fails, revert to the pre-build dir."""
        from bengal.server.build_trigger import _DoubleBuffer

        mgr = self._make_buffer_manager(tmp_path)
        original = mgr.active_dir
        site.output_dir = original
        with (  # noqa: PT012 - mid-context state is the invariant under test
            pytest.raises(RuntimeError),
            _DoubleBuffer(site, mgr, use_incremental=False, last_delta_paths=None) as buf,
        ):
            # We are now writing to staging; build crashes before swap.
            assert site.output_dir == mgr.staging_dir
            assert buf.swapped is False
            raise RuntimeError("build failure")
        # No swap happened, so output_dir reverts to original (still active).
        assert mgr.active_dir == original
        assert site.output_dir == original

    def test_resync_after_failure_with_swap_uses_new_active(
        self, site: MagicMock, tmp_path: Path
    ) -> None:
        """resync_after_failure() after a swap keeps output_dir on new active.

        This is the path the warm build actually uses: the build crashes after
        a swap and handles the exception in-block, calling resync directly.
        """
        from bengal.server.build_trigger import _DoubleBuffer

        mgr = self._make_buffer_manager(tmp_path)
        site.output_dir = mgr.active_dir
        staging_before = mgr.staging_dir
        with _DoubleBuffer(site, mgr, use_incremental=False, last_delta_paths=None) as buf:
            buf.swap()
            buf.resync_after_failure()
        assert site.output_dir == staging_before
        assert mgr.active_dir == staging_before

    def test_resync_after_failure_without_swap_reverts(
        self, site: MagicMock, tmp_path: Path
    ) -> None:
        """resync_after_failure() before a swap reverts to the pre-build dir."""
        from bengal.server.build_trigger import _DoubleBuffer

        mgr = self._make_buffer_manager(tmp_path)
        original = mgr.active_dir
        site.output_dir = original
        with _DoubleBuffer(site, mgr, use_incremental=False, last_delta_paths=None) as buf:
            assert site.output_dir == mgr.staging_dir  # writing to staging
            buf.resync_after_failure()
        assert site.output_dir == original

    def test_incremental_always_syncs_asset_manifest(self, site: MagicMock, tmp_path: Path) -> None:
        """#315: asset-manifest.json is force-synced from active into staging.

        On an incremental delta-staging build the manifest is never in the
        delta paths, but it must be seeded from the active buffer every time so
        the staging (and next active) buffer never serves a stale manifest.
        """
        from bengal.server.build_trigger import _DoubleBuffer

        mgr = self._make_buffer_manager(tmp_path)
        active = mgr.active_dir
        staging = mgr.staging_dir
        # Active buffer has a manifest; staging must be non-empty so the
        # delta-staging path is taken (else it falls back to a full seed).
        (active / "asset-manifest.json").write_text('{"v": "active"}')
        (staging / "placeholder.html").write_text("x")

        site.output_dir = active
        with _DoubleBuffer(
            site,
            mgr,
            use_incremental=True,
            last_delta_paths=(),
        ):
            pass

        # The manifest was force-synced into staging despite empty delta paths.
        synced = staging / "asset-manifest.json"
        assert synced.is_file()
        assert synced.read_text() == '{"v": "active"}'


class TestWarmBuildBufferResync:
    """Guards that _run_warm_build resyncs output_dir on build failure.

    Regression guard: the warm-build failure handling lives inside the
    `with _DoubleBuffer(...)` block, so the resync must be invoked explicitly
    (it cannot rely on __exit__ seeing the already-handled exception).
    """

    def _make_buffer_manager(self, tmp_path: Path) -> object:
        from bengal.server.buffer_manager import BufferManager

        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        return BufferManager(dir_a=dir_a, dir_b=dir_b)

    @patch("bengal.server.build_trigger.execute.show_error")
    @patch("bengal.server.build_trigger.execute.get_dev_server_state")
    def test_warm_build_failure_reverts_output_dir_to_active(
        self,
        mock_state: MagicMock,
        mock_show_error: MagicMock,
        tmp_path: Path,
    ) -> None:
        """A build crash before swap reverts output_dir to the active buffer."""
        mgr = self._make_buffer_manager(tmp_path)
        active = mgr.active_dir

        site = MagicMock()
        site.root_path = tmp_path / "site"
        site.output_dir = active
        site.config = {}
        site.build.side_effect = RuntimeError("boom build")

        trigger = BuildTrigger(
            site=site,
            executor=MagicMock(),
            buffer_manager=mgr,
        )
        cli = MagicMock()

        # Force recovery to fail so self.site stays the original object and we
        # can assert the resync took effect on it.
        with patch(
            "bengal.core.site.Site.from_config",
            side_effect=RuntimeError("no config"),
        ):
            outcome = trigger._run_warm_build(
                changed_paths={Path("x.md")},
                changed_files=["x.md"],
                nav_changed_files=None,
                structural_changed=False,
                use_incremental=True,
                cli=cli,
            )

        assert outcome is None
        assert trigger.site is site
        # No swap ran (build crashed first), so output_dir reverts to active.
        assert trigger.site.output_dir == active
        assert trigger._last_buffer_delta_paths is None
