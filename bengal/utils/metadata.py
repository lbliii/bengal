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

from contextlib import suppress
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal import __version__ as BENGAL_VERSION
from bengal.core.theme import get_theme_package
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

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


def _get_theme_info(site: Site) -> dict[str, Any]:
    theme_name = getattr(site, "theme", None) or "default"
    # Prefer installed theme package metadata when available
    version: str | None = None
    logger = get_logger(__name__)
    try:
        pkg = get_theme_package(theme_name)
        if pkg and pkg.version:
            version = pkg.version
    except Exception as e:
        # Best-effort; ignore errors and fall back to no version
        logger.debug(
            "theme_version_lookup_failed",
            theme=theme_name,
            error=str(e),
            error_type=type(e).__name__,
        )
        pass

    return {"name": theme_name, "version": version}


def _get_i18n_info(config: dict[str, Any]) -> dict[str, Any]:
    i18n = config.get("i18n", {}) or {}
    return {
        "strategy": i18n.get("strategy", "none"),
        "defaultLanguage": i18n.get("default_language", "en"),
        "languages": i18n.get("languages", []),
    }


def _get_capabilities() -> dict[str, bool]:
    """
    Detect runtime capabilities based on installed optional dependencies.

    These are checked once at build time and cached. Templates can use these
    to conditionally enable features (e.g., only emit search-index.json meta
    tag when lunr is installed and will generate the pre-built index).

    Returns:
        Dictionary of capability name → availability boolean
    """
    capabilities: dict[str, bool] = {}

    # Pre-built Lunr search index (requires `pip install bengal[search]`)
    try:
        from lunr import lunr  # type: ignore[import-untyped]  # noqa: F401

        capabilities["prebuilt_search"] = True
    except ImportError:
        capabilities["prebuilt_search"] = False

    # Remote content sources (requires `pip install bengal[github]` etc.)
    try:
        import aiohttp  # type: ignore[import-untyped]  # noqa: F401

        capabilities["remote_content"] = True
    except ImportError:
        capabilities["remote_content"] = False

    return capabilities


def build_template_metadata(site: Site) -> dict[str, Any]:
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

    # Optimization: cache computed metadata on the Site for the duration of a build.
    # This function is called when creating Jinja environments; in parallel builds
    # each worker thread constructs its own Environment, so caching avoids repeating
    # imports/version detection work (mistune/markdown/pygments/theme package).
    #
    # Cache is disabled in dev server mode to reflect config/theme changes quickly.
    if not getattr(site, "dev_mode", False):
        try:
            i18n_info = _get_i18n_info(config)
            cache_key = (
                exposure,
                getattr(site, "theme", None),
                getattr(site, "baseurl", None),
                getattr(getattr(site, "build_time", None), "isoformat", lambda: None)(),
                config.get("markdown_engine"),
                (config.get("markdown", {}) or {}).get("parser"),
                i18n_info.get("strategy"),
                i18n_info.get("defaultLanguage"),
                tuple(i18n_info.get("languages") or []),
            )
            cached = site._bengal_template_metadata_cache
            if (
                isinstance(cached, dict)
                and cached.get("key") == cache_key
                and isinstance(cached.get("metadata"), dict)
            ):
                return cached["metadata"]
        except Exception:
            # Best-effort caching only; never fail metadata generation
            pass

    engine = {"name": "Bengal SSG", "version": BENGAL_VERSION}

    # Always compute full set, then filter based on exposure
    theme_info = _get_theme_info(site)

    # Build info
    logger = get_logger(__name__)
    timestamp: str | None
    try:
        bt = getattr(site, "build_time", None)
        timestamp = bt.isoformat() if isinstance(bt, datetime) else None
    except Exception as e:
        logger.debug(
            "build_timestamp_format_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
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
    capabilities = _get_capabilities()

    full = {
        "engine": engine,
        "theme": theme_info,
        "build": build,
        "rendering": rendering,
        "i18n": i18n,
        "site": {"baseurl": getattr(site, "baseurl", None)},
        "capabilities": capabilities,
    }

    if exposure == "minimal":
        # Capabilities always included (needed for conditional template features)
        result: dict[str, Any] = {"engine": engine, "capabilities": capabilities}
    elif exposure == "standard":
        result = {
            "engine": engine,
            "theme": theme_info,
            "build": build,
            "i18n": i18n,
            "capabilities": capabilities,
        }
    else:  # extended
        result = full

    if not getattr(site, "dev_mode", False):
        with suppress(Exception):
            site._bengal_template_metadata_cache = {"key": cache_key, "metadata": result}

    return result
