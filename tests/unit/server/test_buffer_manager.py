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
        m = BufferManager(base_dir=tmp_path / "buffers")
        m.setup()
        return m

    def test_setup_creates_directories(self, tmp_path: Path) -> None:
        mgr = BufferManager(base_dir=tmp_path / "buffers")
        mgr.setup()
        assert (tmp_path / "buffers" / "a").is_dir()
        assert (tmp_path / "buffers" / "b").is_dir()

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
