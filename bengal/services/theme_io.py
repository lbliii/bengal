"""Theme manifest I/O - reads theme.toml for extends.

Extracted from bengal.core.theme.resolution for core model purity (no I/O in core/).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast

from bengal.core.diagnostics import emit
from bengal.core.theme.registry import get_theme_package
from bengal.themes.utils import THEMES_ROOT


def read_theme_extends(site_root: Path, theme_name: str) -> str | None:
    """Read theme.toml for 'extends' from site, installed, or bundled theme path."""
    # Site theme manifest
    site_manifest = site_root / "themes" / theme_name / "theme.toml"
    if site_manifest.exists():
        try:
            with open(site_manifest, "rb") as f:
                data = tomllib.load(f)
            if isinstance(data, dict):
                extends = data.get("extends")
                return cast(str | None, extends) if extends is not None else None
            return None
        except Exception as e:
            emit(
                None,
                "debug",
                "theme_manifest_read_failed",
                theme=theme_name,
                path=str(site_manifest),
                error=str(e),
                error_type=type(e).__name__,
            )

    # Installed theme manifest
    try:
        pkg = get_theme_package(theme_name)
        if pkg:
            manifest_path = pkg.resolve_resource_path("theme.toml")
            if manifest_path and manifest_path.exists():
                try:
                    with open(manifest_path, "rb") as f:
                        data = tomllib.load(f)
                    extends_val = data.get("extends")
                    return str(extends_val) if extends_val else None
                except Exception as e:
                    emit(
                        None,
                        "debug",
                        "theme_manifest_read_failed",
                        theme=theme_name,
                        path=str(manifest_path),
                        error=str(e),
                        error_type=type(e).__name__,
                    )
    except Exception as e:
        emit(
            None,
            "debug",
            "theme_package_resolve_failed",
            theme=theme_name,
            error=str(e),
            error_type=type(e).__name__,
        )

    # Bundled theme manifest
    bundled_manifest = THEMES_ROOT / theme_name / "theme.toml"
    if bundled_manifest.exists():
        try:
            with open(bundled_manifest, "rb") as f:
                data = tomllib.load(f)
            extends_val = data.get("extends")
            return str(extends_val) if extends_val else None
        except Exception as e:
            emit(
                None,
                "debug",
                "theme_manifest_read_failed",
                theme=theme_name,
                path=str(bundled_manifest),
                error=str(e),
                error_type=type(e).__name__,
            )

    return None
