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
        for template_file in template_files:
            if self.cache.is_changed(template_file):
                if verbose and template_file not in change_summary.modified_templates:
                    change_summary.modified_templates.append(template_file)
                affected = self.cache.get_affected_pages(template_file)
                for page_path_str in affected:
                    pages_to_rebuild.add(Path(page_path_str))
            else:
                self.cache.update_file(template_file)

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
