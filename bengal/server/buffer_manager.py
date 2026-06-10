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


def _hidden_path_component(directory: Path) -> str | None:
    """Return the first hidden (dot-prefixed) component of a resolved path, or None.

    ``.well-known`` is exempt: it is a hidden directory the static handler is
    expected to serve. Mirrors the detection in ``asgi_app._has_hidden_path_component``
    so the construction-time guard (#400) and the request-time serving fallback
    (#392) agree on what "hidden" means.
    """
    try:
        resolved = directory.resolve()
    except OSError:
        resolved = directory
    for part in resolved.parts:
        if part.startswith(".") and part not in {".", "..", ".well-known"}:
            return part
    return None


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
        self._warn_on_hidden_buffer_paths()

    def _warn_on_hidden_buffer_paths(self) -> None:
        """Pin the hidden-path serving constraint at the integration boundary (#400).

        Pounce's static handler rejects any path whose resolved absolute path
        contains a hidden (dot-prefixed) component — see ``pounce/_static.py``
        ``_resolve_file`` and upstream lbliii/pounce#74. The dev server's default
        staging buffer lives under ``<root>/.bengal/staging``, a hidden directory,
        so when that buffer is active Pounce 404s every asset under it. #392 works
        around this by routing those requests through Bengal's own ``_serve_static``,
        but the underlying constraint is invisible three layers from the cause.

        This surfaces the constraint loudly at buffer construction so a future
        change that introduces a *new* hidden serving path fails visibly here
        rather than as mysterious runtime 404s. We log (not raise) because the
        #392 mitigation keeps serving working; Part 2 (relocating the staging
        buffer off ``.bengal/``) is upstream-gated on pounce#74.
        """
        for label, directory in (("active", self._dirs[0]), ("staging", self._dirs[1])):
            hidden = _hidden_path_component(directory)
            if hidden is not None:
                logger.warning(
                    "buffer_path_hidden_component",
                    buffer=label,
                    path=str(directory),
                    hidden_component=hidden,
                    ref="lbliii/pounce#74",
                    hint=(
                        "Buffer path contains a hidden (dot-prefixed) component that "
                        "Pounce's static handler rejects; asset requests for this buffer "
                        "fall back to bengal's _serve_static (#392 mitigation) instead of "
                        "the fast Pounce static path. Relocating off .bengal/ (#400 Part 2) "
                        "is gated on upstream pounce#74."
                    ),
                )

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

    def prepare_delta_staging(
        self,
        changed_paths: Iterable[Path | str],
        *,
        always_sync: Iterable[Path | str] = (),
    ) -> Path:
        """Bring staging up to date by syncing only known changed outputs.

        The inactive buffer is usually a complete snapshot from the previous
        generation. After one successful incremental swap it only differs from
        active by that build's changed outputs, so copying just those paths is
        enough to make staging a complete base for the next incremental build.
        If staging is empty or a path cannot be made relative safely, this
        falls back to the full hardlink seed.

        ``always_sync`` lists output paths that must be seeded from the active
        buffer on *every* delta-staging, regardless of ``changed_paths``. These
        are infrastructure files (notably ``asset-manifest.json``) whose content
        describes the *currently served* buffer rather than a stable per-file
        output: a content-only rebuild never rewrites them, so they would never
        appear in ``changed_paths`` and would otherwise drift a generation behind
        across swaps — leaving a buffer serving a stale/divergent manifest (#315).
        Seeding them from active each time keeps both buffers consistent.
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

        forced = self._sync_always(always_sync, active, staging)

        logger.debug(
            "staging_delta_seeded",
            files=synced,
            removed=removed,
            forced=forced,
            active=str(active),
            staging=str(staging),
        )
        return staging

    def _sync_always(
        self,
        always_sync: Iterable[Path | str],
        active: Path,
        staging: Path,
    ) -> int:
        """Unconditionally re-seed infrastructure paths from active into staging.

        Mirrors the per-file hardlink/copy used elsewhere. A path absent from the
        active buffer is removed from staging so the two stay consistent. Unsafe
        paths are skipped (they cannot escape the buffer root). Returns the number
        of files synced for logging.
        """
        forced = 0
        for raw_path in always_sync:
            rel_path = self._normalize_relative_output_path(Path(raw_path), active)
            if rel_path is None:
                # Should not happen for the build's own infrastructure paths, but
                # log it (rather than silently dropping) so an unexpected unsafe
                # path surfaces instead of manifesting as a mystery stale manifest.
                logger.debug(
                    "staging_always_sync_skipped", reason="unsafe_path", path=str(raw_path)
                )
                continue
            src_path = active / rel_path
            dst_path = staging / rel_path
            if not src_path.is_file():
                if dst_path.is_file():
                    dst_path.unlink()
                continue
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            if dst_path.exists():
                dst_path.unlink()
            try:
                os.link(src_path, dst_path)
            except OSError:
                shutil.copy2(src_path, dst_path)
            forced += 1
        return forced

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
