"""Tests for BufferManager double-buffered output."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from bengal.server.buffer_manager import BufferManager


def _atomic_write(path: Path, content: str) -> None:
    """Write via temp+rename to break hardlinks (matches build pipeline)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(content)
        Path(tmp).replace(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class TestBufferManager:
    """Tests for BufferManager."""

    @pytest.fixture
    def mgr(self, tmp_path: Path) -> BufferManager:
        """Create a BufferManager with temporary directories."""
        m = BufferManager(dir_a=tmp_path / "a", dir_b=tmp_path / "b")
        m.setup()
        return m

    def test_setup_creates_directories(self, tmp_path: Path) -> None:
        mgr = BufferManager(dir_a=tmp_path / "a", dir_b=tmp_path / "b")
        mgr.setup()
        assert (tmp_path / "a").is_dir()
        assert (tmp_path / "b").is_dir()

    def test_for_dev_server_factory(self, tmp_path: Path) -> None:
        out = tmp_path / "public"
        staging = tmp_path / ".bengal" / "staging"
        mgr = BufferManager.for_dev_server(out, staging)
        mgr.setup()
        assert mgr.active_dir == out
        assert mgr.staging_dir == staging
        assert out.is_dir()
        assert staging.is_dir()

    def test_initial_active_is_a(self, mgr: BufferManager) -> None:
        assert mgr.active_dir.name == "a"
        assert mgr.staging_dir.name == "b"

    def test_swap_flips_active_and_staging(self, mgr: BufferManager) -> None:
        mgr.swap()
        assert mgr.active_dir.name == "b"
        assert mgr.staging_dir.name == "a"

    def test_swap_increments_generation(self, mgr: BufferManager) -> None:
        assert mgr.generation == 0
        mgr.swap()
        assert mgr.generation == 1
        mgr.swap()
        assert mgr.generation == 2

    def test_double_swap_returns_to_original(self, mgr: BufferManager) -> None:
        original = mgr.active_dir
        mgr.swap()
        mgr.swap()
        assert mgr.active_dir == original

    def test_prepare_staging_returns_staging_dir(self, mgr: BufferManager) -> None:
        staging = mgr.prepare_staging()
        assert staging == mgr.staging_dir

    def test_prepare_staging_seeds_from_active(self, mgr: BufferManager) -> None:
        active = mgr.active_dir
        (active / "index.html").write_text("<html>hello</html>")
        (active / "posts").mkdir()
        (active / "posts" / "index.html").write_text("<html>post</html>")

        staging = mgr.prepare_staging()

        assert (staging / "index.html").read_text() == "<html>hello</html>"
        assert (staging / "posts" / "index.html").read_text() == "<html>post</html>"

    def test_hardlink_seeding_shares_inodes(self, mgr: BufferManager) -> None:
        active = mgr.active_dir
        (active / "page.html").write_text("<html>test</html>")

        staging = mgr.prepare_staging()

        active_inode = (active / "page.html").stat().st_ino
        staging_inode = (staging / "page.html").stat().st_ino
        assert active_inode == staging_inode

    def test_atomic_overwrite_breaks_hardlink(self, mgr: BufferManager) -> None:
        """Atomic writes (temp+rename) create new inodes, leaving active intact."""
        active = mgr.active_dir
        (active / "page.html").write_text("<html>original</html>")

        staging = mgr.prepare_staging()
        _atomic_write(staging / "page.html", "<html>updated</html>")

        assert (active / "page.html").read_text() == "<html>original</html>"
        assert (staging / "page.html").read_text() == "<html>updated</html>"

    def test_direct_write_shares_through_hardlink(self, mgr: BufferManager) -> None:
        """Direct write_text() writes through hardlinks (same inode).

        This is why the build pipeline MUST use atomic writes when
        double buffering is active.
        """
        active = mgr.active_dir
        (active / "page.html").write_text("<html>original</html>")

        staging = mgr.prepare_staging()
        (staging / "page.html").write_text("<html>oops</html>")

        assert (active / "page.html").read_text() == "<html>oops</html>"

    def test_prepare_staging_cleans_old_content(self, mgr: BufferManager) -> None:
        staging = mgr.staging_dir
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "stale.html").write_text("old")

        mgr.prepare_staging()

        assert not (staging / "stale.html").exists()

    def test_prepare_staging_no_clean(self, mgr: BufferManager) -> None:
        staging = mgr.staging_dir
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "keep.html").write_text("keep")

        mgr.prepare_staging(clean=False)

        assert (staging / "keep.html").exists()

    def test_prepare_delta_staging_syncs_changed_files(self, mgr: BufferManager) -> None:
        active = mgr.active_dir
        staging = mgr.staging_dir
        (active / "index.html").write_text("<html>v2</html>")
        (active / "unchanged.html").write_text("<html>same</html>")
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "index.html").write_text("<html>v1</html>")
        (staging / "unchanged.html").write_text("<html>same</html>")

        result = mgr.prepare_delta_staging([Path("index.html")])

        assert result == staging
        assert (staging / "index.html").read_text() == "<html>v2</html>"
        assert (staging / "unchanged.html").read_text() == "<html>same</html>"
        assert (active / "index.html").stat().st_ino == (staging / "index.html").stat().st_ino

    def test_prepare_delta_staging_removes_missing_outputs(self, mgr: BufferManager) -> None:
        active = mgr.active_dir
        staging = mgr.staging_dir
        (active / "index.html").write_text("<html>keep</html>")
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "stale.html").write_text("<html>old</html>")

        mgr.prepare_delta_staging([Path("stale.html")])

        assert not (staging / "stale.html").exists()

    def test_prepare_delta_staging_falls_back_when_staging_empty(self, mgr: BufferManager) -> None:
        active = mgr.active_dir
        (active / "index.html").write_text("<html>seeded</html>")

        staging = mgr.prepare_delta_staging([Path("index.html")])

        assert (staging / "index.html").read_text() == "<html>seeded</html>"

    def test_delta_staging_does_not_sync_unlisted_files(self, mgr: BufferManager) -> None:
        """A file neither in changed_paths nor always_sync is left untouched.

        This is the divergence mechanism behind #315: asset-manifest.json is never
        in the delta paths (a content-only rebuild does not rewrite it), so without
        always_sync it drifts a generation behind in the staging buffer.
        """
        active = mgr.active_dir
        staging = mgr.staging_dir
        (active / "asset-manifest.json").write_text('{"gen": 2}')
        (active / "index.html").write_text("<html>v2</html>")
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "asset-manifest.json").write_text('{"gen": 1}')
        (staging / "index.html").write_text("<html>v1</html>")

        mgr.prepare_delta_staging([Path("index.html")])

        # The manifest was NOT in changed_paths, so plain delta-staging leaves the
        # staging buffer's stale copy in place — it diverges from active.
        assert (staging / "asset-manifest.json").read_text() == '{"gen": 1}'

    def test_delta_staging_always_sync_refreshes_manifest(self, mgr: BufferManager) -> None:
        """always_sync re-seeds the manifest from active even when it is not changed (#315)."""
        active = mgr.active_dir
        staging = mgr.staging_dir
        (active / "asset-manifest.json").write_text('{"gen": 2}')
        (active / "index.html").write_text("<html>v2</html>")
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "asset-manifest.json").write_text('{"gen": 1}')
        (staging / "index.html").write_text("<html>v1</html>")

        mgr.prepare_delta_staging([Path("index.html")], always_sync=["asset-manifest.json"])

        # Now the staging buffer carries the active buffer's current manifest, so it
        # will not serve a stale/divergent manifest after the next swap.
        assert (staging / "asset-manifest.json").read_text() == '{"gen": 2}'
        # And it shares active's inode (hardlinked, atomic-write-safe).
        assert (active / "asset-manifest.json").stat().st_ino == (
            staging / "asset-manifest.json"
        ).stat().st_ino

    def test_delta_staging_always_sync_removes_when_absent_in_active(
        self, mgr: BufferManager
    ) -> None:
        """If active lacks an always_sync file, it is removed from staging (stay consistent)."""
        active = mgr.active_dir
        staging = mgr.staging_dir
        (active / "index.html").write_text("<html>v2</html>")
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "index.html").write_text("<html>v1</html>")
        (staging / "asset-manifest.json").write_text('{"gen": 1}')

        mgr.prepare_delta_staging([Path("index.html")], always_sync=["asset-manifest.json"])

        assert not (staging / "asset-manifest.json").exists()

    def test_delta_staging_fallback_full_seed_keeps_manifest_consistent(
        self, mgr: BufferManager
    ) -> None:
        """When delta-staging falls back to a full seed, the manifest is still synced.

        ``prepare_delta_staging`` returns early to ``prepare_staging`` when staging is
        empty (or a path is unsafe), so ``_sync_always`` is not reached. That is safe
        because the full hardlink seed copies *every* file — including the manifest —
        so the buffers stay consistent without the explicit always_sync pass.
        """
        active = mgr.active_dir
        (active / "index.html").write_text("<html>v2</html>")
        (active / "asset-manifest.json").write_text('{"gen": 2}')
        # Staging is empty -> prepare_delta_staging falls back to a full seed.

        staging = mgr.prepare_delta_staging(
            [Path("index.html")], always_sync=["asset-manifest.json"]
        )

        assert (staging / "asset-manifest.json").read_text() == '{"gen": 2}', (
            "the full-seed fallback must also leave the staging buffer with the "
            "active buffer's current manifest"
        )

    def test_full_cycle(self, mgr: BufferManager) -> None:
        """Simulate: build to staging, swap, build again to new staging.

        Uses atomic writes to correctly break hardlinks between buffers.
        """
        # First build: write to staging (b)
        staging = mgr.prepare_staging()
        _atomic_write(staging / "index.html", "<html>v1</html>")
        mgr.swap()

        assert mgr.active_dir.name == "b"
        assert (mgr.active_dir / "index.html").read_text() == "<html>v1</html>"

        # Second build: stage to a, seed from b
        staging = mgr.prepare_staging()
        assert (staging / "index.html").read_text() == "<html>v1</html>"
        _atomic_write(staging / "index.html", "<html>v2</html>")
        mgr.swap()

        assert mgr.active_dir.name == "a"
        assert (mgr.active_dir / "index.html").read_text() == "<html>v2</html>"
        # Old buffer still has v1
        assert (mgr.staging_dir / "index.html").read_text() == "<html>v1</html>"
