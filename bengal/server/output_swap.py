"""
Output directory double-buffering for crash-safe dev server rebuilds.

Builds write to a staging directory, then an atomic rename swaps staging
into the live serving path. The ASGI app always reads from a complete,
consistent output tree — eliminating partial-output races that cause
emergency template fallbacks during rapid edits.

Architecture:
    BuildTrigger → prepare_staging() → site.build(output_dir=staging)
                 → commit_staging()  → ASGI app sees new output atomically

    On build failure:
    BuildTrigger → rollback_staging() → live dir untouched

Related:
    bengal/server/build_trigger.py: Calls prepare/commit/rollback
    bengal/server/asgi_app.py: Reads from live_dir
    bengal/server/dev_server.py: Calls cleanup_swap_artifacts on startup
"""

from __future__ import annotations

import contextlib
import os
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

STAGING_DIR_NAME = ".staging"
OLD_DIR_NAME = ".public.old"


@dataclass(frozen=True, slots=True)
class SwapConfig:
    """Paths for the double-buffer swap.

    All three directories must be on the same filesystem for atomic rename.
    This is guaranteed because staging_dir is under live_dir's parent.
    """

    live_dir: Path
    staging_dir: Path
    old_dir: Path

    @classmethod
    def from_output_dir(cls, output_dir: Path) -> SwapConfig:
        """Derive swap paths from the live output directory."""
        return cls(
            live_dir=output_dir,
            staging_dir=output_dir.parent / STAGING_DIR_NAME,
            old_dir=output_dir.parent / OLD_DIR_NAME,
        )


def prepare_staging(config: SwapConfig) -> Path:
    """Create a clean staging directory for the next build.

    Removes any leftover staging from a prior crashed build, then creates
    a fresh empty directory.

    Returns:
        Path to the staging directory (ready for build output).
    """
    if config.staging_dir.exists():
        shutil.rmtree(config.staging_dir, ignore_errors=True)
    config.staging_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("staging_prepared", path=str(config.staging_dir))
    return config.staging_dir


def commit_staging(config: SwapConfig) -> None:
    """Atomically swap the staging directory into the live serving path.

    Sequence:
        1. Rename live → old  (atomic, same FS)
        2. Rename staging → live  (atomic, same FS)
        3. Delete old in background thread

    If step 2 fails (extremely unlikely — same FS rename), step 1 is
    reversed to restore the live directory.
    """
    if not config.staging_dir.exists():
        logger.warning("commit_staging_skipped", reason="staging_dir_missing")
        return

    # Clean up any prior old dir (from crashed swap or prior build)
    if config.old_dir.exists():
        shutil.rmtree(config.old_dir, ignore_errors=True)

    try:
        os.rename(config.live_dir, config.old_dir)
    except OSError as e:
        logger.error(
            "swap_failed_live_to_old",
            error=str(e),
            live=str(config.live_dir),
            old=str(config.old_dir),
        )
        raise

    try:
        os.rename(config.staging_dir, config.live_dir)
    except OSError as e:
        # Restore live from old to avoid serving nothing
        logger.error(
            "swap_failed_staging_to_live",
            error=str(e),
            staging=str(config.staging_dir),
            live=str(config.live_dir),
        )
        with contextlib.suppress(OSError):
            os.rename(config.old_dir, config.live_dir)
        raise

    logger.debug("staging_committed", live=str(config.live_dir))

    # Background cleanup of old directory (non-blocking)
    threading.Thread(
        target=_cleanup_old_dir,
        args=(config.old_dir,),
        daemon=True,
        name="bengal-swap-cleanup",
    ).start()


def rollback_staging(config: SwapConfig) -> None:
    """Discard staging on build failure, leaving the live directory intact."""
    if config.staging_dir.exists():
        shutil.rmtree(config.staging_dir, ignore_errors=True)
        logger.debug("staging_rolled_back", path=str(config.staging_dir))


def cleanup_swap_artifacts(output_dir: Path) -> None:
    """Remove leftover swap artifacts from prior crashed runs.

    Called once at dev server startup to ensure a clean slate.
    """
    config = SwapConfig.from_output_dir(output_dir)
    cleaned = False
    for d in (config.staging_dir, config.old_dir):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            logger.info("swap_artifact_cleaned", path=str(d))
            cleaned = True
    if not cleaned:
        logger.debug("swap_artifacts_clean", output_dir=str(output_dir))


def _cleanup_old_dir(old_dir: Path) -> None:
    """Background cleanup of the old directory after successful swap."""
    try:
        shutil.rmtree(old_dir, ignore_errors=True)
    except Exception as e:
        logger.debug("old_dir_cleanup_failed", error=str(e))
