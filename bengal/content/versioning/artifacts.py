"""
Versioning build artifacts: versions.json and root redirect.

Emits Mike-compatible versions.json and optional root redirect HTML
when versioning is enabled. Used during build finalization.

Format (Mike-compatible):
    [{"version": "1.0", "title": "1.0.1", "aliases": ["latest"], "url_prefix": ""}, ...]

Related:
- bengal/core/version.py: VersionConfig
- bengal/orchestration/build/finalization.py: phase_collect_stats
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.version import VersionConfig


def build_versions_json(version_config: VersionConfig) -> list[dict[str, Any]]:
    """
    Build Mike-compatible versions.json structure from VersionConfig.

    Args:
        version_config: Site versioning configuration

    Returns:
        List of version dicts for JSON serialization
    """
    result: list[dict[str, Any]] = []
    for v in version_config.versions:
        # Find aliases pointing to this version
        aliases = [alias for alias, vid in version_config.aliases.items() if vid == v.id]
        result.append(
            {
                "version": v.id,
                "title": v.label or v.id,
                "aliases": aliases,
                "url_prefix": v.url_prefix,
            }
        )
    return result


def write_versions_json(site: Any, output_dir: Path) -> None:
    """
    Write versions.json to output directory when versioning enabled.

    Emits to public/versions.json (or deploy_prefix/versions.json if set).
    Only runs when versioning.enabled and versioning.emit_versions_json (default True).

    Args:
        site: Site instance with version_config
        output_dir: Output directory (e.g. site.output_dir)
    """
    version_config = getattr(site, "version_config", None)
    if not version_config or not version_config.enabled:
        return

    config = getattr(site, "config", {}) or {}
    versioning = config.get("versioning", {}) or {}
    if hasattr(versioning, "_data"):
        versioning = versioning._data
    emit = versioning.get("emit_versions_json", True)
    if not emit:
        return

    data = build_versions_json(version_config)
    if not data:
        return

    json_text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    # Check deploy_prefix from versioning config
    deploy_prefix = versioning.get("deploy_prefix", "") or ""
    target_dir = output_dir / deploy_prefix.strip("/") if deploy_prefix else output_dir

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "versions.json"

    from bengal.utils.io.atomic_write import AtomicFile

    _write_if_changed_atomic(target_path, json_text, AtomicFile)


def write_root_redirect(site: Any, output_dir: Path) -> None:
    """
    Write root index.html redirect to default version when enabled.

    Creates a meta-refresh + JS redirect page at output_dir/index.html.
    Only runs when versioning.default_redirect is True. Overwrites any
    existing index.html at root—use only for docs-only versioned sites.

    Args:
        site: Site instance with version_config
        output_dir: Output directory
    """
    version_config = getattr(site, "version_config", None)
    if not version_config or not version_config.enabled:
        return

    config = getattr(site, "config", {}) or {}
    versioning = config.get("versioning", {}) or {}
    if hasattr(versioning, "_data"):
        versioning = versioning._data
    if not versioning.get("default_redirect", False):
        return

    latest = version_config.latest_version
    if not latest:
        return

    # Default redirect target: first versioned section for latest
    # Latest has no url_prefix, so /docs/ for sections=["docs"]
    target = versioning.get("default_redirect_target")
    if not target:
        sections = version_config.sections
        target = f"/{sections[0]}/" if sections else "/"

    # Ensure target starts with /
    if not target.startswith("/"):
        target = "/" + target
    # Ensure target ends with / for directory
    if not target.endswith("/"):
        target = target + "/"

    baseurl = config.get("baseurl", "") or ""
    href = baseurl.rstrip("/") + target

    html = _redirect_html(href)

    from bengal.utils.io.atomic_write import AtomicFile

    target_path = output_dir / "index.html"
    _write_if_changed_atomic(target_path, html, AtomicFile)


def _redirect_html(href: str) -> str:
    """Generate HTML redirect page (meta refresh + JS fallback).

    Escapes href for safe use in HTML attributes and JS string literals.
    """
    href_attr = html.escape(href, quote=True)
    href_js = json.dumps(href)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0;url={href_attr}">
<link rel="canonical" href="{href_attr}">
<title>Redirecting...</title>
<script>window.location.replace({href_js});</script>
</head>
<body><p>Redirecting to <a href="{href_attr}">documentation</a>...</p></body>
</html>
"""


def _write_if_changed_atomic(path: Path, content: str, atomic_file_cls: type) -> None:
    """Write file atomically only if content differs."""
    try:
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if existing == content:
                return
    except Exception:
        pass

    with atomic_file_cls(path, "w", encoding="utf-8") as f:
        f.write(content)
