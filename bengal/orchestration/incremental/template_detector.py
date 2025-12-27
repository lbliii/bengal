"""
Template change detection for incremental builds.

Handles checking template files for changes and tracking affected pages.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.core.site import Site
    from bengal.orchestration.build.results import ChangeSummary

logger = get_logger(__name__)

# Threshold for switching from sequential to parallel processing.
PARALLEL_THRESHOLD = 50

# Default max workers for parallel operations
DEFAULT_MAX_WORKERS = min(8, (os.cpu_count() or 4))


def _get_max_workers(site: Site) -> int:
    """Get max workers from site config or use default."""
    return site.config.get("max_workers", DEFAULT_MAX_WORKERS)


class TemplateChangeDetector:
    """
    Detects changes in template files and tracks affected pages.

    Collects all template files first, then checks in parallel if above threshold.
    """

    def __init__(
        self,
        site: Site,
        cache: BuildCache,
    ) -> None:
        """
        Initialize template change detector.

        Args:
            site: Site instance for configuration and paths
            cache: BuildCache for change detection
        """
        self.site = site
        self.cache = cache

    def check_templates(
        self,
        *,
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Check templates for changes.

        Collects all template files first, then checks in parallel if above threshold.
        """
        template_files: list[Path] = []

        # Collect all template files
        theme_templates_dir = self._get_theme_templates_dir()
        if theme_templates_dir and theme_templates_dir.exists():
            template_files.extend(theme_templates_dir.rglob("*.html"))

        site_templates_dir = self.site.root_path / "templates"
        if site_templates_dir.exists():
            template_files.extend(site_templates_dir.rglob("*.html"))

        if not template_files:
            return

        if len(template_files) < PARALLEL_THRESHOLD:
            self._check_templates_sequential(
                template_files, pages_to_rebuild, change_summary, verbose
            )
        else:
            self._check_templates_parallel(
                template_files, pages_to_rebuild, change_summary, verbose
            )

    def _check_templates_sequential(
        self,
        template_files: list[Path],
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Sequential template checking for small workloads."""
        changed_template_names: list[str] = []

        for template_file in template_files:
            if self.cache.is_changed(template_file):
                if verbose and template_file not in change_summary.modified_templates:
                    change_summary.modified_templates.append(template_file)
                affected = self.cache.get_affected_pages(template_file)
                for page_path_str in affected:
                    pages_to_rebuild.add(Path(page_path_str))

                # Collect template name for optional cache invalidation
                template_name = self._path_to_template_name(template_file)
                if template_name:
                    changed_template_names.append(template_name)
            else:
                self.cache.update_file(template_file)

        # Optional: Help template engine clear cache if it supports it
        if changed_template_names:
            self._invalidate_engine_cache(changed_template_names)

    def _check_templates_parallel(
        self,
        template_files: list[Path],
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Parallel template checking for large workloads.

        Note: cache.update_file() is called sequentially after parallel check
        to avoid potential race conditions in cache updates.
        """
        max_workers = _get_max_workers(self.site)
        results_lock = Lock()
        unchanged_templates: list[Path] = []
        unchanged_lock = Lock()

        def check_single_template(template_file: Path) -> tuple[Path, bool, set[str]]:
            """Check a single template (thread-safe read operations only)."""
            changed = self.cache.is_changed(template_file)
            affected: set[str] = set()
            if changed:
                affected = self.cache.get_affected_pages(template_file)
            return (template_file, changed, affected)

        changed_template_names: list[str] = []
        changed_names_lock = Lock()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(check_single_template, t): t for t in template_files}

            for future in as_completed(futures):
                try:
                    template_file, changed, affected = future.result()
                    if changed:
                        with results_lock:
                            if verbose and template_file not in change_summary.modified_templates:
                                change_summary.modified_templates.append(template_file)
                            for page_path_str in affected:
                                pages_to_rebuild.add(Path(page_path_str))

                        # Collect template name for optional cache invalidation
                        template_name = self._path_to_template_name(template_file)
                        if template_name:
                            with changed_names_lock:
                                changed_template_names.append(template_name)
                    else:
                        with unchanged_lock:
                            unchanged_templates.append(template_file)
                except Exception as e:
                    template_file = futures[future]
                    logger.warning(
                        "template_change_check_failed",
                        template=str(template_file),
                        error=str(e),
                    )

        # Update unchanged templates sequentially (cache writes should be serialized)
        for template_file in unchanged_templates:
            self.cache.update_file(template_file)

        # Optional: Help template engine clear cache if it supports it
        if changed_template_names:
            self._invalidate_engine_cache(changed_template_names)

    def _get_theme_templates_dir(self) -> Path | None:
        """Get the templates directory for the current theme."""
        # Be defensive: site.theme may be None, a string, or a Mock in tests
        theme = self.site.theme
        if not theme or not isinstance(theme, str):
            return None

        site_theme_dir = self.site.root_path / "themes" / theme / "templates"
        if site_theme_dir.exists():
            return site_theme_dir

        import bengal

        bengal_dir = Path(bengal.__file__).parent
        bundled_theme_dir = bengal_dir / "themes" / theme / "templates"
        if bundled_theme_dir.exists():
            return bundled_theme_dir

        return None

    def _path_to_template_name(self, template_path: Path) -> str | None:
        """Convert template file path to template name (relative to template dirs).

        Template names are relative to template directories, e.g.:
        - Path: /site/themes/default/templates/base.html
        - Name: base.html

        Args:
            template_path: Absolute path to template file

        Returns:
            Template name relative to template directory, or None if not found
        """
        try:
            # Check site templates directory first
            site_templates_dir = self.site.root_path / "templates"
            if site_templates_dir.exists():
                try:
                    rel_path = template_path.relative_to(site_templates_dir)
                    return str(rel_path.as_posix())
                except ValueError:
                    pass

            # Check theme templates directory
            theme_templates_dir = self._get_theme_templates_dir()
            if theme_templates_dir and theme_templates_dir.exists():
                try:
                    rel_path = template_path.relative_to(theme_templates_dir)
                    return str(rel_path.as_posix())
                except ValueError:
                    pass
        except Exception:
            # If path conversion fails, return None (cache invalidation is optional)
            pass

        return None

    def _invalidate_engine_cache(self, template_names: list[str]) -> None:
        """Optionally invalidate template engine cache if engine supports it.

        This is an optional optimization. Engines that support cache invalidation
        (like Kida) can benefit from faster cache clearing when Bengal detects
        template changes. Engines without this method will continue to work normally
        (they handle invalidation internally).

        Args:
            template_names: List of template names to invalidate
        """
        try:
            # Get template engine instance
            from bengal.rendering.engines import create_engine

            engine = create_engine(self.site)

            # Check if engine supports cache invalidation (optional method)
            if hasattr(engine, "clear_template_cache"):
                engine.clear_template_cache(template_names)
                logger.debug(
                    "template_engine_cache_invalidated",
                    engine=type(engine).__name__,
                    templates=len(template_names),
                )
        except Exception as e:
            # Cache invalidation is optional - log but don't fail
            logger.debug(
                "template_engine_cache_invalidation_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
