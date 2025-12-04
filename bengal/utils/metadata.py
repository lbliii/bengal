"""
Metadata utilities for build information and template metadata.

Provides functions for generating build metadata including version information,
markdown engine details, syntax highlighter versions, and theme information.
Used for template metadata generation and build information reporting.

Key Concepts:
    - Build metadata: Version information for Bengal and dependencies
    - Markdown engine detection: Resolves configured markdown parser and version
    - Syntax highlighter detection: Pygments version detection
    - Theme information: Theme name and version from theme packages

Related Modules:
    - bengal.utils.theme_registry: Theme package lookup
    - bengal.rendering.template_engine: Template engine using metadata
    - bengal.utils.build_stats: Build statistics collection

See Also:
    - bengal/utils/metadata.py:build_template_metadata() for metadata generation
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bengal import __version__ as BENGAL_VERSION
from bengal.utils.logger import get_logger
from bengal.utils.theme_registry import get_theme_package

logger = get_logger(__name__)


def _get_markdown_engine_and_version(config: dict[str, Any]) -> tuple[str, str | None]:
    """
    Determine configured markdown engine and resolve its library version.
    """
    # Support legacy flat key and new nested config
    engine = config.get("markdown_engine")
    if not engine:
        md_cfg = config.get("markdown", {}) or {}
        engine = md_cfg.get("parser", "mistune")

    version: str | None = None
    try:
        if engine == "mistune":
            import mistune  # type: ignore

            version = getattr(mistune, "__version__", None)
        elif engine in ("python-markdown", "markdown", "python_markdown"):
            import markdown  # type: ignore

            version = getattr(markdown, "__version__", None)
    except Exception as e:
        logger.debug("markdown_version_detect_failed", engine=engine, error=str(e))

    return str(engine), version


def _get_highlighter_version() -> str | None:
    try:
        import pygments  # type: ignore

        return getattr(pygments, "__version__", None)
    except Exception as e:
        logger.debug("pygments_version_detect_failed", error=str(e))
        return None


def _get_theme_info(site) -> dict[str, Any]:
    theme_name = getattr(site, "theme", None) or "default"
    # Prefer installed theme package metadata when available
    version: str | None = None
    try:
        pkg = get_theme_package(theme_name)
        if pkg and pkg.version:
            version = pkg.version
    except Exception:
        # Best-effort; ignore errors and fall back to no version
        pass

    return {"name": theme_name, "version": version}


def _get_i18n_info(config: dict[str, Any]) -> dict[str, Any]:
    i18n = config.get("i18n", {}) or {}
    return {
        "strategy": i18n.get("strategy", "none"),
        "defaultLanguage": i18n.get("default_language", "en"),
        "languages": i18n.get("languages", []),
    }


def build_template_metadata(site) -> dict[str, Any]:
    """
    Build a curated, privacy-aware metadata dictionary for templates/JS.

    Exposure levels (via config['expose_metadata']):
      - minimal: engine only
      - standard: + theme, build timestamp, i18n basics
      - extended: + rendering details (markdown/highlighter versions)
    """
    config = getattr(site, "config", {}) or {}
    exposure = (config.get("expose_metadata") or "minimal").strip().lower()
    if exposure not in ("minimal", "standard", "extended"):
        exposure = "minimal"

    engine = {"name": "Bengal SSG", "version": BENGAL_VERSION}

    # Always compute full set, then filter based on exposure
    theme_info = _get_theme_info(site)

    # Build info
    timestamp: str | None
    try:
        bt = getattr(site, "build_time", None)
        timestamp = bt.isoformat() if isinstance(bt, datetime) else None
    except Exception:
        timestamp = None

    build = {"timestamp": timestamp}

    # Rendering info
    md_engine, md_version = _get_markdown_engine_and_version(config)
    rendering = {
        "markdown": md_engine,
        "markdownVersion": md_version,
        "highlighter": "pygments",
        "highlighterVersion": _get_highlighter_version(),
    }

    i18n = _get_i18n_info(config)

    full = {
        "engine": engine,
        "theme": theme_info,
        "build": build,
        "rendering": rendering,
        "i18n": i18n,
        "site": {"baseurl": getattr(site, "baseurl", None)},
    }

    if exposure == "minimal":
        return {"engine": engine}
    elif exposure == "standard":
        return {
            "engine": engine,
            "theme": theme_info,
            "build": build,
            "i18n": i18n,
        }
    else:  # extended
        return full
