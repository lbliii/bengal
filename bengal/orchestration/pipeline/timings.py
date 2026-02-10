"""
Persisted task timing hints for profile-guided pipeline scheduling.

Stores a rolling estimate of per-task durations under ``.bengal/state`` and
feeds those estimates into the DAG scheduler so ready tasks are ordered by
critical-path priority.
"""

from __future__ import annotations

import json
from pathlib import Path

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

_TIMINGS_FILE = "pipeline_task_timings.json"
_EWMA_ALPHA = 0.35


def _timings_path(root_path: Path) -> Path:
    return root_path / ".bengal" / "state" / _TIMINGS_FILE


def load_task_timings(root_path: Path) -> dict[str, float]:
    """Load persisted task duration estimates in milliseconds."""
    path = _timings_path(root_path)
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text())
    except Exception as exc:
        logger.debug(
            "pipeline_timing_load_failed",
            path=str(path),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return {}

    if not isinstance(raw, dict):
        return {}

    timings: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, int | float) and value > 0:
            timings[key] = float(value)
    return timings


def update_task_timings(root_path: Path, observed_ms: dict[str, float]) -> None:
    """Merge observed task timings using EWMA and persist to disk."""
    if not observed_ms:
        return

    merged = load_task_timings(root_path)
    for task_name, observed in observed_ms.items():
        if observed <= 0:
            continue
        previous = merged.get(task_name, observed)
        merged[task_name] = (1 - _EWMA_ALPHA) * previous + _EWMA_ALPHA * observed

    path = _timings_path(root_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(merged, sort_keys=True))
    temp_path.replace(path)
