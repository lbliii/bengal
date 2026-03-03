"""
Stale output purge for incremental builds.

RFC: stale-output-purge - Removes output files not produced by the current
build. Enables correct deploys without --clean-output when posts are removed,
URLs change, or taxonomy terms are deleted.

Key Concepts:
- Output manifest: Set of paths written this build (from BuildOutputCollector)
- Purge phase: Walk output_dir, delete files not in manifest
- Keep files: .git, .nojekyll, .gitignore never deleted

Related Modules:
- bengal.core.output: BuildOutputCollector.get_manifest_paths()
- bengal.orchestration.build: Phase 17.5 integration

"""

from __future__ import annotations

from pathlib import Path

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

_KEEP_FILES: frozenset[str] = frozenset({".git", ".nojekyll", ".gitignore"})


def purge_stale_outputs(
    output_dir: Path,
    manifest: frozenset[str],
    keep_files: frozenset[str] = _KEEP_FILES,
) -> int:
    """Remove files in output_dir that are not in the manifest.

    Walks output_dir, deletes any file whose relative path is not in manifest.
    Respects keep_files (basenames) to never delete .git, .nojekyll, etc.

    Args:
        output_dir: Base output directory to purge
        manifest: Set of relative paths (posix-normalized) to keep
        keep_files: Basenames to never delete (e.g. .nojekyll)

    Returns:
        Count of deleted files

    """
    if not output_dir.exists():
        return 0

    deleted = 0

    for path in output_dir.rglob("*"):
        if path.is_dir():
            continue

        try:
            rel = path.relative_to(output_dir)
        except ValueError:
            continue

        rel_posix = str(rel).replace("\\", "/")

        if rel_posix in manifest:
            continue
        if path.name in keep_files:
            continue

        try:
            path.unlink(missing_ok=True)
            deleted += 1
            logger.debug("purged_stale_output", path=rel_posix)
        except OSError as e:
            logger.warning(
                "purge_failed",
                path=rel_posix,
                error=str(e),
            )

    # Remove empty directories (bottom-up via sorted by depth descending)
    dirs_to_check = sorted(
        (p for p in output_dir.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    )
    for d in dirs_to_check:
        try:
            if d != output_dir and d.exists() and not any(d.iterdir()):
                d.rmdir()
        except OSError:
            pass

    if deleted > 0:
        logger.info("purge_stale_outputs_complete", deleted=deleted)

    return deleted
