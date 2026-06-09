"""
Crossover gate for the isolated render backend — issue #350, saga S5.

Decides whether a given render phase should use the separate-heap backend or the
in-process thread path. The isolated backend wins only for *large cold builds*:
it pays a fixed per-worker startup + (for spawn) transport cost that the dev loop
and incremental builds can't amortize, and immortalization leaks for the process
lifetime — fine for one-shot CLI/CI, never the long-running dev server. So the
gate is conservative and opt-in:

- ``render_isolation`` config (``[build]``): ``off`` (default), ``auto``,
  ``fork``, or ``spawn``.
- ``render_isolation_threshold``: page-count crossover (default 400; calibrate
  with ``benchmarks/calibrate_render_isolation.py``).
- ``render_isolation_workers``: optional worker-count override.

Environment overrides (handy for CI without editing config):
``BENGAL_RENDER_ISOLATION``, ``BENGAL_RENDER_ISOLATION_THRESHOLD``,
``BENGAL_RENDER_ISOLATION_WORKERS``.

The gate only ever *enables* isolation for cold, parallel, snapshot-backed
builds above the crossover; everything else falls through to the thread path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

__all__ = [
    "DEFAULT_THRESHOLD",
    "IsolationDecision",
    "IsolationSettings",
    "decide_isolation",
    "resolve_isolation_settings",
]

DEFAULT_THRESHOLD = 400
_VALID_MODES = ("off", "auto", "fork", "spawn", "shard")


@dataclass(frozen=True, slots=True)
class IsolationSettings:
    """Resolved isolation configuration (config + env overrides applied)."""

    mode: str = "off"
    threshold: int = DEFAULT_THRESHOLD
    workers: int | None = None


@dataclass(frozen=True, slots=True)
class IsolationDecision:
    """Outcome of the gate for one render phase."""

    enabled: bool
    mode: str  # "fork" | "spawn" | "off"
    reason: str
    threshold: int = DEFAULT_THRESHOLD
    workers: int | None = None


def _build_value(config: Any, key: str) -> Any:
    """Read a ``[build]`` value from a typed Config or a plain dict."""
    build_section = getattr(config, "build", None)
    if build_section is not None and not isinstance(build_section, dict):
        return getattr(build_section, key, None)
    if isinstance(build_section, dict):
        return build_section.get(key)
    if isinstance(config, dict):
        section = config.get("build", {})
        if isinstance(section, dict):
            return section.get(key)
    return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def resolve_isolation_settings(config: Any) -> IsolationSettings:
    """
    Resolve isolation settings from ``[build]`` config, with env overrides.

    Env vars take precedence over config so CI/CLI can opt in without editing a
    site's config file.
    """
    mode = _build_value(config, "render_isolation") or "off"
    env_mode = os.environ.get("BENGAL_RENDER_ISOLATION")
    if env_mode:
        mode = env_mode
    mode = str(mode).strip().lower()
    if mode not in _VALID_MODES:
        mode = "off"

    threshold = _int_or_none(_build_value(config, "render_isolation_threshold"))
    env_threshold = _int_or_none(os.environ.get("BENGAL_RENDER_ISOLATION_THRESHOLD"))
    if env_threshold is not None:
        threshold = env_threshold
    if threshold is None or threshold < 0:
        threshold = DEFAULT_THRESHOLD

    workers = _int_or_none(_build_value(config, "render_isolation_workers"))
    env_workers = _int_or_none(os.environ.get("BENGAL_RENDER_ISOLATION_WORKERS"))
    if env_workers is not None:
        workers = env_workers
    if workers is not None and workers <= 0:
        workers = None

    return IsolationSettings(mode=mode, threshold=threshold, workers=workers)


def decide_isolation(
    settings: IsolationSettings,
    *,
    page_count: int,
    incremental: bool,
    parallel: bool,
    has_snapshot: bool,
    fork_available: bool,
) -> IsolationDecision:
    """
    Decide whether to use the isolated backend for this render phase.

    Isolation is enabled only for large, cold, parallel, snapshot-backed builds
    above the crossover. Any other condition falls through to the thread path.
    """

    def off(reason: str) -> IsolationDecision:
        return IsolationDecision(
            enabled=False,
            mode="off",
            reason=reason,
            threshold=settings.threshold,
            workers=settings.workers,
        )

    if settings.mode == "off":
        return off("render_isolation=off")
    if not parallel:
        return off("sequential render")
    if incremental:
        return off("incremental build (dev/loop path)")
    if not has_snapshot:
        return off("no snapshot available")
    if page_count < settings.threshold:
        return off(f"below crossover ({page_count} < {settings.threshold})")

    # spawn backend is not implemented yet; "auto"/"fork" select the Phase-1 fork backend,
    # "shard" selects the Phase-2 COW-free re-parsing shard backend (#350 S13.4g).
    if settings.mode == "spawn":
        return off("spawn backend not yet implemented")
    if not fork_available:
        return off("fork start method unavailable")

    backend_mode = "shard" if settings.mode == "shard" else "fork"
    return IsolationDecision(
        enabled=True,
        mode=backend_mode,
        reason=f"cold build, {page_count} >= {settings.threshold} pages",
        threshold=settings.threshold,
        workers=settings.workers,
    )
