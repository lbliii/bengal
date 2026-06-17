"""Git-derived metadata helpers for content files."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

logger = get_logger(__name__)


def find_git_root(start: Path) -> Path | None:
    """Return the git repository root containing ``start``, or None."""
    path = start.resolve()
    if not path.is_dir():
        path = path.parent

    for candidate in [path, *path.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def batch_git_last_modified(
    paths: Sequence[Path],
    *,
    repo_root: Path | None = None,
) -> dict[Path, datetime]:
    """
    Batch-resolve last commit dates for content files via ``git log``.

    Uses a single ``git log --name-only`` pass and keeps the first (most
    recent) commit date encountered for each tracked file.

    Returns an empty dict when git is unavailable, the tree is not a repo,
    or the subprocess fails (shallow CI clones, sandbox builds, etc.).

    Args:
        paths: Absolute or repo-relative source file paths.
        repo_root: Optional git root. When omitted, inferred from the first path.

    Returns:
        Mapping of resolved absolute paths to UTC commit datetimes.
    """
    if not paths:
        return {}

    resolved_paths = [path.resolve() for path in paths]
    root = repo_root or find_git_root(resolved_paths[0])
    if root is None:
        return {}

    rel_paths: list[str] = []
    rel_to_abs: dict[str, Path] = {}
    for path in resolved_paths:
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        rel_paths.append(rel)
        rel_to_abs[rel] = path

    if not rel_paths:
        return {}

    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "log",
                "--format=%cI",
                "--name-only",
                "--",
                *rel_paths,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("git_lastmod_lookup_failed", error=str(exc))
        return {}

    if completed.returncode != 0:
        logger.debug(
            "git_lastmod_lookup_nonzero",
            returncode=completed.returncode,
            stderr=completed.stderr.strip(),
        )
        return {}

    wanted = set(rel_paths)
    results: dict[Path, datetime] = {}
    current_date: datetime | None = None

    for raw_line in completed.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parsed = _parse_git_timestamp(line)
        if parsed is not None:
            current_date = parsed
            continue

        if current_date is None or line not in wanted or line in results:
            continue

        abs_path = rel_to_abs.get(line)
        if abs_path is not None:
            results[abs_path] = current_date

    return results


def _parse_git_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).replace(tzinfo=None)
