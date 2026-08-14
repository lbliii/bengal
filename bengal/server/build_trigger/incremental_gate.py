"""Incremental vs full rebuild gate for the dev-server rebuild loop.

Decides whether a watcher batch can stay incremental or must take a full
rebuild (templates, autodoc, SVG icons, shared/version config).
"""

from pathlib import Path
from typing import Any

from bengal.protocols import SiteLike
from bengal.utils.observability.logger import get_logger
from bengal.utils.paths.normalize import to_posix

logger = get_logger("bengal.server.build_trigger")


def _needs_full_rebuild(
    trigger: Any,
    changed_paths: set[Path],
    event_types: set[str],
) -> bool:
    """
    Determine if a full rebuild is needed.

    Full rebuild triggers:
    - Structural changes (created/deleted/moved files)
    - Template changes (.html in templates/themes)
    - Autodoc source changes (.py, OpenAPI specs)
    - SVG icon changes (inlined in HTML)
    - Shared content changes (_shared/ directory) [versioned sites]
    - Version config changes (versioning.yaml)
    """
    # Structural changes always need full rebuild
    if {"created", "deleted", "moved"} & event_types:
        return True

    # Check for template changes
    if trigger._is_template_change(changed_paths):
        logger.debug("full_rebuild_triggered_by_template")
        return True

    # Check for autodoc changes
    if trigger._should_regenerate_autodoc(changed_paths):
        logger.debug("full_rebuild_triggered_by_autodoc")
        return True

    # Check for SVG icon changes (inlined in HTML)
    for path in changed_paths:
        path_str = to_posix(path)
        if (
            path.suffix.lower() == ".svg"
            and "/themes/" in path_str
            and "/assets/icons/" in path_str
        ):
            logger.debug("full_rebuild_triggered_by_svg", file=str(path))
            return True

    # RFC: rfc-versioned-docs-pipeline-integration
    # Check for shared content changes (forces full rebuild for versioned sites)
    if trigger._is_shared_content_change(changed_paths):
        logger.debug("full_rebuild_triggered_by_shared_content")
        return True

    # Check for version config changes (forces full rebuild)
    if trigger._is_version_config_change(changed_paths):
        logger.debug("full_rebuild_triggered_by_version_config")
        return True

    return False


def _get_template_dirs(trigger: Any) -> list[Path]:
    """
    Get template directories (cached).

    Caches the list of existing template directories to avoid
    repeated exists() calls on every file change check.

    Returns:
        List of existing template directories
    """
    if trigger._template_dirs is not None:
        return trigger._template_dirs

    root_path = trigger.site.root_path

    if not root_path:
        trigger._template_dirs = []
        return trigger._template_dirs

    from bengal.rendering.template_engine.environment import resolve_template_dirs

    trigger._template_dirs = resolve_template_dirs(trigger.site)
    return trigger._template_dirs


def _is_template_change(trigger: Any, changed_paths: set[Path]) -> bool:
    """
    Check if template changes require full rebuild.

    Instead of full rebuild for any template change, uses dependency tracking
    to determine if incremental rebuild is possible.

    Returns True only if:
    1. Changed templates have dependents AND
    2. Incremental template update isn't possible

    Optimizations:
    1. Filter to .html files first (skip non-templates early)
    2. Use cached template directories (avoids exists() calls)
    3. Check dependency graph to skip orphan templates
    """
    template_dirs = trigger._get_template_dirs()
    if not template_dirs:
        return False

    # Filter to .html files first (early exit optimization)
    html_paths = [p for p in changed_paths if p.suffix.lower() == ".html"]
    if not html_paths:
        return False

    # Get cache for dependency tracking
    cache = getattr(trigger.site, "_cache", None)
    if cache is None:
        # Try to get cache from site's cache manager or incremental orchestrator
        try:
            from bengal.cache import BuildCache

            cache_path = trigger.site.config_service.paths.build_cache
            if cache_path.exists():
                cache = BuildCache.load(cache_path)
                cache.site_root = trigger.site.root_path
        except Exception as e:
            # A corrupt/unreadable build cache must not crash the watcher,
            # but the swallow used to hide load failures entirely. Emit a
            # breadcrumb so a missing template-dependency graph (which
            # forces conservative full rebuilds) is explainable.
            logger.debug(
                "template_cache_load_failed",
                cache_path=str(cache_path),
                error=str(e),
                error_type=type(e).__name__,
                action="treating template change as full rebuild (no dependency graph)",
            )
            cache = None

    for path in html_paths:
        if not trigger._is_in_template_dir(path, template_dirs):
            continue

        affected, dependency_data_known = trigger._get_template_dependents(
            path,
            cache,
            template_dirs,
        )

        if not affected:
            if dependency_data_known:
                # Template has no dependents - skip entirely
                logger.debug(
                    "template_change_ignored",
                    template=str(path),
                    reason="no_dependents",
                )
                continue

            logger.debug(
                "template_change_full_rebuild",
                template=str(path),
                affected_pages=0,
                reason="dependency_data_missing",
            )
            logger.info(
                "template_change_full_rebuild",
                template=str(path),
                affected_pages=0,
                reason="dependency_data_missing",
                suggestion="Run one full build to populate template dependency data.",
            )
            return True

        # Has dependents - check if we can do incremental update
        if trigger._can_use_incremental_template_update(path, cache):
            logger.info(
                "template_change_incremental",
                template=str(path),
                affected_pages=len(affected),
            )
            continue  # Will be handled by incremental build

        # Must do full rebuild
        logger.info(
            "template_change_full_rebuild",
            template=str(path),
            affected_pages=len(affected),
            reason="incremental_not_possible",
        )
        return True

    return False


def _template_name_for_path(trigger: Any, path: Path, template_dirs: list[Path]) -> str:
    """Return the template name used by BuildCache dependency indexes."""
    from bengal.rendering.template_engine.environment import template_name_for_path

    return template_name_for_path(path, template_dirs)


def _get_template_dependents(
    trigger: Any,
    path: Path,
    cache: Any,
    template_dirs: list[Path],
) -> tuple[set[str], bool]:
    """Return pages affected by a template and whether dependency data was known."""
    if cache is None:
        return set(), False

    template_name = trigger._template_name_for_path(path, template_dirs)
    template_dependencies = getattr(cache, "template_dependencies", None)
    if isinstance(template_dependencies, dict) and template_dependencies:
        try:
            return set(cache.get_pages_for_template(template_name)), True
        except Exception as exc:
            logger.debug(
                "template_dependency_lookup_failed",
                template=template_name,
                error=str(exc),
            )

    try:
        affected = set(cache.get_affected_pages(path))
    except Exception as exc:
        logger.debug(
            "template_reverse_dependency_lookup_failed",
            template=str(path),
            error=str(exc),
        )
        return set(), False

    return affected, bool(affected)


def _is_in_template_dir(trigger: Any, path: Path, template_dirs: list[Path]) -> bool:
    """Check if path is within any template directory."""
    try:
        resolved_path = path.resolve()
    except OSError, ValueError:
        resolved_path = path

    for template_dir in template_dirs:
        try:
            resolved_dir = template_dir.resolve()
            resolved_path.relative_to(resolved_dir)
            return True
        except ValueError, OSError:
            continue
    return False


def _can_use_incremental_template_update(trigger: Any, template_path: Path, cache: Any) -> bool:
    """
    Check if incremental template update is possible.

    Incremental update is possible when:
    1. Block-level detection is available (Kida engine)
    2. Only site-scoped blocks changed (nav, footer, etc.)
    3. All affected pages can be re-rendered individually

    Args:
        template_path: Path to the changed template
        cache: BuildCache instance or None

    Returns:
        True if incremental update is possible
    """
    try:
        from bengal.protocols import EngineCapability
        from bengal.rendering.engines import create_engine

        # Check if template engine supports block-level detection via capability
        engine = create_engine(trigger.site)
        if not engine.has_capability(EngineCapability.BLOCK_LEVEL_DETECTION):
            return False

        template_dependencies = getattr(cache, "template_dependencies", None)
        return isinstance(template_dependencies, dict) and bool(template_dependencies)
    except Exception as exc:
        logger.debug(
            "template_incremental_check_failed",
            template=str(template_path),
            error=str(exc),
        )
        return False


def _should_regenerate_autodoc(trigger: Any, changed_paths: set[Path]) -> bool:
    """Check if autodoc regeneration is needed."""
    if not isinstance(trigger.site, SiteLike) or not trigger.site.config:
        return False

    # ConfigSection now supports dict methods, use directly
    autodoc_config = trigger.site.config.get("autodoc", {})

    # Check Python source directories
    python_config = autodoc_config.get("python", {})
    if python_config.get("enabled", False):
        source_dirs = python_config.get("source_dirs", [])
        for path in changed_paths:
            for source_dir in source_dirs:
                source_path = trigger.site.root_path / source_dir
                try:
                    path.relative_to(source_path)
                    if path.suffix == ".py":
                        return True
                except ValueError:
                    continue

    # Check OpenAPI spec
    openapi_config = autodoc_config.get("openapi", {})
    if openapi_config.get("enabled", False):
        spec_file = openapi_config.get("spec_file")
        if spec_file:
            spec_path = trigger.site.root_path / spec_file
            for path in changed_paths:
                if path == spec_path or path.resolve() == spec_path.resolve():
                    return True

        try:
            cache = getattr(trigger.site, "_cache", None)
            if cache is None:
                from bengal.cache import BuildCache

                cache_path = trigger.site.config_service.paths.build_cache
                if cache_path.exists():
                    cache = BuildCache.load(cache_path)

            if cache is not None and hasattr(cache, "autodoc_tracker"):
                for source in cache.autodoc_tracker.get_autodoc_source_files():
                    source_path = Path(source)
                    candidates = [source_path]
                    if not source_path.is_absolute():
                        candidates.extend(
                            [
                                trigger.site.root_path / source_path,
                                trigger.site.root_path.parent / source_path,
                            ]
                        )
                    resolved_candidates = {candidate.resolve() for candidate in candidates}
                    for path in changed_paths:
                        if path.resolve() in resolved_candidates:
                            return True
        except Exception as exc:
            logger.debug(
                "autodoc_dependency_change_check_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )

    return False
