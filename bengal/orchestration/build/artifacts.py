"""
Build-time artifact writing.

Extracted from finalization.py. Writes build badge (SVG/JSON) and versioning
artifacts into the output directory. Used during phase_collect_stats.
"""

from __future__ import annotations

import json
from typing import Any

from bengal.utils.io.atomic_write import write_if_changed_atomic


def write_build_time_artifacts(site: Any, last_build_stats: dict[str, Any]) -> None:
    """
    Write build-time artifacts into the output directory (opt-in).

    Why this exists:
        `BuildStats.build_time_ms` is only finalized after templates render (Phase 19).
        Writing a small SVG/JSON artifact here allows templates to display build time
        accurately by referencing a static path like `/bengal/build.svg`.

    """
    config = getattr(site, "config", {}) or {}
    build_badge_cfg = normalize_build_badge_config(config.get("build_badge"))
    if not build_badge_cfg["enabled"]:
        return

    output_dir = getattr(site, "output_dir", None)
    if not output_dir:
        return

    import os
    from pathlib import Path

    from bengal.orchestration.badge import build_shields_like_badge_svg, format_duration_ms_compact
    from bengal.utils.concurrency.workers import WorkloadType, get_optimal_workers

    duration_ms = float(last_build_stats.get("build_time_ms") or 0)
    duration_text = format_duration_ms_compact(duration_ms)

    # Get CPU/worker stats for context
    cpu_count = os.cpu_count() or 0
    # Report optimal workers for a typical mixed workload
    max_workers = get_optimal_workers(
        100,
        workload_type=WorkloadType.MIXED,
        config_override=config.get("max_workers"),
    )
    parallel = last_build_stats.get("parallel", True)
    incremental = last_build_stats.get("incremental", False)
    skipped = last_build_stats.get("skipped", False)
    cache_hits = int(last_build_stats.get("cache_hits") or 0)

    # Determine build mode (cold/warm)
    # Cold: full rebuild (not incremental) OR incremental but no cache hits
    # Warm: incremental with cache hits
    build_mode = "full"
    if skipped:
        build_mode = "skipped"
    elif incremental:
        build_mode = "warm" if cache_hits > 0 else "cold"

    payload = {
        "build_time_ms": duration_ms,
        "build_time_human": duration_text,
        "total_pages": int(last_build_stats.get("total_pages") or 0),
        "total_assets": int(last_build_stats.get("total_assets") or 0),
        "rendering_time_ms": float(last_build_stats.get("rendering_time_ms") or 0),
        "timestamp": _safe_isoformat(getattr(site, "build_time", None)),
        "parallel": parallel,
        "incremental": incremental,
        "build_mode": build_mode,
        "cpu_count": cpu_count,
        "worker_count": max_workers if parallel else 1,
    }

    # Add block cache stats if available (RFC: kida-template-introspection)
    block_cache_hits = int(last_build_stats.get("block_cache_hits") or 0)
    block_cache_site_blocks = int(last_build_stats.get("block_cache_site_blocks") or 0)
    if block_cache_site_blocks > 0 or block_cache_hits > 0:
        payload["block_cache"] = {
            "site_blocks_cached": block_cache_site_blocks,
            "hits": block_cache_hits,
            "misses": int(last_build_stats.get("block_cache_misses") or 0),
            "time_saved_ms": float(last_build_stats.get("block_cache_time_saved_ms") or 0.0),
        }

    svg = build_shields_like_badge_svg(
        label=build_badge_cfg["label"],
        message=duration_text,
        label_color=build_badge_cfg["label_color"],
        message_color=build_badge_cfg["message_color"],
    )
    json_text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    for root in _iter_output_roots(site):
        target_dir = Path(root) / build_badge_cfg["dir_name"]
        target_dir.mkdir(parents=True, exist_ok=True)

        write_if_changed_atomic(target_dir / "build.svg", svg)
        write_if_changed_atomic(target_dir / "build.json", json_text)


def write_versioning_artifacts(site: Any) -> None:
    """
    Write versioning artifacts when versioning is enabled.

    Emits versions.json (Mike-compatible) and optional root redirect.
    """
    output_dir = getattr(site, "output_dir", None)
    if not output_dir:
        return

    from pathlib import Path

    from bengal.content.versioning.artifacts import write_root_redirect, write_versions_json

    write_versions_json(site, Path(output_dir))
    write_root_redirect(site, Path(output_dir))


def normalize_build_badge_config(value: Any) -> dict[str, Any]:
    """
    Normalize `build_badge` config.

    Supported:
      - False / None: disabled
      - True: enabled with defaults
      - {enabled: bool, ...}: enabled with overrides

    """
    if value is None or value is False:
        return {
            "enabled": False,
            "dir_name": "bengal",
            "label": "built in",
            "label_color": "#555",
            "message_color": "#4c1d95",
        }

    if value is True:
        return {
            "enabled": True,
            "dir_name": "bengal",
            "label": "built in",
            "label_color": "#555",
            "message_color": "#4c1d95",
        }

    if isinstance(value, dict):
        enabled = bool(value.get("enabled", True))
        return {
            "enabled": enabled,
            "dir_name": str(value.get("dir_name", "bengal")),
            "label": str(value.get("label", "built in")),
            "label_color": str(value.get("label_color", "#555")),
            "message_color": str(value.get("message_color", "#4c1d95")),
        }

    # Unknown type: treat as disabled rather than guessing.
    return {
        "enabled": False,
        "dir_name": "bengal",
        "label": "built in",
        "label_color": "#555",
        "message_color": "#4c1d95",
    }


def _iter_output_roots(site: Any) -> list[Any]:
    """
    Determine which output roots should receive build artifacts.

    For i18n prefix strategy, some sites render into language subdirectories.
    We mirror the behavior of site-wide outputs by also writing into those
    subdirectories so that `/en/bengal/build.svg` resolves when the site is
    deployed under a language prefix.

    """
    output_dir = getattr(site, "output_dir", None)
    if not output_dir:
        return []

    roots: list[Any] = [output_dir]

    config = getattr(site, "config", {}) or {}
    i18n = config.get("i18n", {}) or {}
    if i18n.get("strategy") != "prefix":
        return roots

    default_lang = str(i18n.get("default_language", "en"))
    default_in_subdir = bool(i18n.get("default_in_subdir", False))

    lang_codes: list[str] = []
    for entry in i18n.get("languages", []) or []:
        if isinstance(entry, str):
            lang_codes.append(entry)
        elif isinstance(entry, dict):
            code = entry.get("code") or entry.get("lang") or entry.get("language")
            if isinstance(code, str) and code:
                lang_codes.append(code)

    for code in sorted(set(lang_codes)):
        if code == default_lang and not default_in_subdir:
            continue
        roots.append(_join(output_dir, code))

    if default_in_subdir:
        roots.append(_join(output_dir, default_lang))

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[Any] = []
    for r in roots:
        key = str(r)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


def _join(root: Any, child: str) -> Any:
    from pathlib import Path

    return Path(root) / child


def _safe_isoformat(value: Any) -> str | None:
    try:
        from datetime import datetime

        if isinstance(value, datetime):
            return value.isoformat()
        return None
    except Exception:
        return None
