"""Double-buffered output directory manager for the dev server.

Manages two buffer directories so the ASGI app always serves from a
complete, consistent snapshot while the next build writes to a separate
staging directory. After a build finishes, an in-process reference swap
makes the staging buffer active — no symlinks, no filesystem overhead,
cross-platform.

Usage (dev_server.py / build_trigger.py):

    # Use the standard output_dir as buffer A and .bengal/staging as B:
    mgr = BufferManager.for_dev_server(output_dir, staging_dir)

    # Before each build:
    staging = mgr.prepare_staging()  # hardlink-seeds from active if populated
    site.output_dir = staging

    # After build completes:
    mgr.swap()

    # ASGI app resolves on each request:
    serving_dir = mgr.active_dir
"""

from __future__ import annotations

import os
import shutil
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = get_logger(__name__)


class BufferManager:
    """Thread-safe double-buffer manager with in-process reference swap."""

    def __init__(self, dir_a: Path, dir_b: Path) -> None:
        self._dirs: tuple[Path, Path] = (dir_a, dir_b)
        self._active_idx: int = 0
        self._lock = threading.Lock()
        self._generation: int = 0

    @classmethod
    def for_dev_server(cls, output_dir: Path, staging_dir: Path) -> BufferManager:
        """Create a BufferManager where buffer A is the standard output_dir.

        This avoids copying on startup — the initial build writes to
        output_dir as usual, and the first rebuild writes to staging_dir.
        """
        return cls(dir_a=output_dir, dir_b=staging_dir)

    def setup(self) -> None:
        """Create buffer directories if they don't exist."""
        for d in self._dirs:
            d.mkdir(parents=True, exist_ok=True)

    @property
    def active_dir(self) -> Path:
        """Directory the ASGI app should serve from (snapshot at call time)."""
        with self._lock:
            return self._dirs[self._active_idx]

    @property
    def staging_dir(self) -> Path:
        """Directory the next build should write to."""
        with self._lock:
            return self._dirs[1 - self._active_idx]

    @property
    def generation(self) -> int:
        """Monotonic counter incremented on each swap."""
        with self._lock:
            return self._generation

    def prepare_staging(self, *, clean: bool = True) -> Path:
        """Prepare the staging buffer for a new build.

        If the active buffer has content, seeds the staging buffer via
        hardlinks so incremental builds only overwrite changed files.
        Otherwise, ensures the staging directory exists and is empty.

        Args:
            clean: If True (default), remove existing staging content
                before seeding. Set False to keep existing staging content.

        Returns:
            Path to the staging directory, ready for the build to write to.
        """
        staging = self.staging_dir
        active = self.active_dir

        if clean and staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=True)

        active_has_content = active.exists() and any(active.iterdir())
        if active_has_content:
            self._seed_via_hardlinks(active, staging)

        return staging

    def prepare_delta_staging(self, changed_paths: Iterable[Path | str]) -> Path:
        """Bring staging up to date by syncing only known changed outputs.

        The inactive buffer is usually a complete snapshot from the previous
        generation. After one successful incremental swap it only differs from
        active by that build's changed outputs, so copying just those paths is
        enough to make staging a complete base for the next incremental build.
        If staging is empty or a path cannot be made relative safely, this
        falls back to the full hardlink seed.
        """
        staging = self.staging_dir
        active = self.active_dir

        if not staging.exists() or not any(staging.iterdir()):
            return self.prepare_staging()

        staging.mkdir(parents=True, exist_ok=True)

        synced = 0
        removed = 0
        for raw_path in changed_paths:
            rel_path = self._normalize_relative_output_path(Path(raw_path), active)
            if rel_path is None:
                logger.debug(
                    "staging_delta_seed_fallback",
                    reason="unsafe_path",
                    path=str(raw_path),
                )
                return self.prepare_staging()

            src_path = active / rel_path
            dst_path = staging / rel_path

            if src_path.is_dir():
                dst_path.mkdir(parents=True, exist_ok=True)
                continue

            if not src_path.exists():
                if dst_path.is_dir():
                    shutil.rmtree(dst_path)
                    removed += 1
                elif dst_path.exists():
                    dst_path.unlink()
                    removed += 1
                continue

            dst_path.parent.mkdir(parents=True, exist_ok=True)
            if dst_path.is_dir():
                shutil.rmtree(dst_path)
            elif dst_path.exists():
                dst_path.unlink()

            try:
                os.link(src_path, dst_path)
            except OSError:
                shutil.copy2(src_path, dst_path)
            synced += 1

        logger.debug(
            "staging_delta_seeded",
            files=synced,
            removed=removed,
            active=str(active),
            staging=str(staging),
        )
        return staging

    def swap(self) -> int:
        """Atomically swap staging to active.

        Returns the new generation number. All subsequent calls to
        ``active_dir`` will return what was previously ``staging_dir``.
        """
        with self._lock:
            self._active_idx = 1 - self._active_idx
            self._generation += 1
            gen = self._generation

        logger.debug(
            "buffer_swap",
            active=str(self.active_dir),
            generation=gen,
        )
        return gen

    def _seed_via_hardlinks(self, src: Path, dst: Path) -> None:
        """Seed dst from src using hardlinks for O(1)-per-file copying.

        Hardlinks share inodes — the build will break the link when it
        overwrites a file, creating a new inode for the changed content
        while the active buffer's file remains untouched.

        Falls back to regular copy if hardlinking fails (e.g. cross-device).
        """
        count = 0
        for src_path in src.rglob("*"):
            rel = src_path.relative_to(src)
            dst_path = dst / rel

            if src_path.is_dir():
                dst_path.mkdir(parents=True, exist_ok=True)
                continue

            dst_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(src_path, dst_path)
            except OSError:
                shutil.copy2(src_path, dst_path)
            count += 1

        logger.debug("staging_seeded", files=count, src=str(src), dst=str(dst))

    def _normalize_relative_output_path(self, path: Path, active: Path) -> Path | None:
        """Normalize an output path so it cannot escape the buffer root."""
        if path.is_absolute():
            try:
                path = path.resolve().relative_to(active.resolve())
            except OSError, ValueError:
                return None

        if any(part == ".." for part in path.parts):
            return None
        return path
