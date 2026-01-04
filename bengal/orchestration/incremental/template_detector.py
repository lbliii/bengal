"""
Template change detection for incremental builds.

Handles checking template files for changes and tracking affected pages.
Supports block-level detection when Kida engine is available.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger
from bengal.utils.workers import WorkloadType, get_optimal_workers, should_parallelize

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.core.site import Site
    from bengal.orchestration.build.results import ChangeSummary
    from bengal.orchestration.incremental.rebuild_decision import (
        RebuildDecision,
        RebuildDecisionEngine,
    )
    from bengal.rendering.block_cache import BlockCache
    from bengal.rendering.engines.kida import KidaTemplateEngine

logger = get_logger(__name__)

# Note: PARALLEL_THRESHOLD and DEFAULT_MAX_WORKERS are deprecated
# in favor of should_parallelize() and get_optimal_workers()
# Kept for backwards compatibility if accessed directly
PARALLEL_THRESHOLD = 50
DEFAULT_MAX_WORKERS = min(8, (os.cpu_count() or 4))


class TemplateChangeDetector:
    """
    Detects changes in template files and tracks affected pages.

    Collects all template files first, then checks in parallel if above threshold.

    Block-Level Detection:
        When `block_cache` is provided and Kida engine is used, enables
        block-level change detection. This can skip page rebuilds entirely
        when only site-scoped blocks (nav, footer, header) change.

    Thread-Safety:
        Uses cached engine and context to avoid repeated initialization.
        Thread-safe for concurrent template checks.
    """

    def __init__(
        self,
        site: Site,
        cache: BuildCache,
        block_cache: BlockCache | None = None,
    ) -> None:
        """
        Initialize template change detector.

        Args:
            site: Site instance for configuration and paths
            cache: BuildCache for change detection
            block_cache: Optional BlockCache for block-level detection
        """
        self.site = site
        self.cache = cache
        self.block_cache = block_cache

        # Lazy-initialized components for block-level detection
        # (avoid engine creation until needed)
        self._engine: KidaTemplateEngine | None = None
        self._decision_engine: RebuildDecisionEngine | None = None
        self._site_context: dict | None = None

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

        # Template change detection is I/O-bound (stat calls)
        if not should_parallelize(len(template_files), workload_type=WorkloadType.IO_BOUND):
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
        """Sequential template checking for small workloads.

        If block-level detection is available, uses it to skip page rebuilds
        when only site-scoped blocks change.
        """
        changed_template_names: list[str] = []
        blocks_rewarmed = 0
        pages_skipped = 0

        for template_file in template_files:
            if self.cache.is_changed(template_file):
                if verbose and template_file not in change_summary.modified_templates:
                    change_summary.modified_templates.append(template_file)

                template_name = self._path_to_template_name(template_file)

                # Try block-level detection first
                if template_name and self._can_use_block_detection():
                    decision = self._decide_block_level(template_name, template_file)

                    if decision.skip_all_pages:
                        # Just re-warm blocks, skip page rebuilds!
                        self._rewarm_blocks(template_name, decision.blocks_to_rewarm)
                        blocks_rewarmed += len(decision.blocks_to_rewarm)
                        pages_skipped += len(self.cache.get_affected_pages(template_file))
                        logger.info(
                            "template_change_block_level",
                            template=template_file.name,
                            blocks_rewarmed=list(decision.blocks_to_rewarm),
                            pages_skipped=True,
                            reason=decision.reason,
                        )
                        # Update file hash so we don't recheck next build
                        self.cache.update_file(template_file)
                        continue

                    # Add only affected pages from decision
                    pages_to_rebuild.update(decision.pages_to_rebuild)
                    if decision.blocks_to_rewarm:
                        self._rewarm_blocks(template_name, decision.blocks_to_rewarm)
                        blocks_rewarmed += len(decision.blocks_to_rewarm)
                else:
                    # Fallback to file-level (current behavior)
                    affected = self.cache.get_affected_pages(template_file)
                    for page_path_str in affected:
                        pages_to_rebuild.add(Path(page_path_str))

                if template_name:
                    changed_template_names.append(template_name)
            # Unchanged templates don't need fingerprint updates.
            # If content is unchanged, the existing fingerprint is valid.

        # Log block-level savings
        if blocks_rewarmed > 0 or pages_skipped > 0:
            logger.info(
                "block_level_incremental_savings",
                blocks_rewarmed=blocks_rewarmed,
                pages_skipped=pages_skipped,
            )

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
        # Access max_workers from build section (supports both Config and dict)
        config = self.site.config
        if hasattr(config, "build"):
            max_workers_override = config.build.max_workers
        else:
            build_section = config.get("build", {})
            max_workers_override = (
                build_section.get("max_workers")
                if isinstance(build_section, dict)
                else config.get("max_workers")
            )

        max_workers = get_optimal_workers(
            len(template_files),
            workload_type=WorkloadType.IO_BOUND,
            config_override=max_workers_override,
        )
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

        # Unchanged templates don't need fingerprint updates.
        # The existing fingerprint is valid if content hasn't changed.
        _ = unchanged_templates  # Suppress unused variable warning

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

    # =========================================================================
    # Block-Level Detection (RFC: block-level-incremental-builds)
    # =========================================================================

    def _get_engine(self) -> KidaTemplateEngine:
        """Get or create cached engine instance.

        Reuses engine across multiple template checks to avoid
        repeated initialization overhead.
        """
        if self._engine is None:
            from bengal.rendering.engines import create_engine

            self._engine = create_engine(self.site)
        return self._engine

    def _get_site_context(self) -> dict:
        """Get or create cached site context."""
        if self._site_context is None:
            from bengal.rendering.context import get_engine_globals

            self._site_context = get_engine_globals(self.site)
        return self._site_context

    def _get_decision_engine(self) -> RebuildDecisionEngine:
        """Get or create cached decision engine."""
        if self._decision_engine is None:
            from bengal.orchestration.incremental.block_detector import (
                BlockChangeDetector,
            )
            from bengal.orchestration.incremental.rebuild_decision import (
                RebuildDecisionEngine,
            )

            engine = self._get_engine()
            block_detector = BlockChangeDetector(engine, self.block_cache)
            self._decision_engine = RebuildDecisionEngine(
                block_detector=block_detector,
                block_cache=self.block_cache,
                build_cache=self.cache,
                engine=engine,
            )
        return self._decision_engine

    def _can_use_block_detection(self) -> bool:
        """Check if block-level detection is available for this site."""
        if self.block_cache is None:
            return False

        # Check if engine supports block-level detection via capability
        try:
            from bengal.rendering.engines import create_engine
            from bengal.rendering.engines.protocol import EngineCapability

            engine = create_engine(self.site)
            return engine.has_capability(EngineCapability.BLOCK_LEVEL_DETECTION)
        except Exception:
            return False

    def _decide_block_level(
        self,
        template_name: str,
        template_path: Path,
    ) -> RebuildDecision:
        """Make block-level rebuild decision for a template change.

        Args:
            template_name: Template name (e.g., "base.html")
            template_path: Path to template file

        Returns:
            RebuildDecision with blocks to re-warm and pages to rebuild
        """
        from bengal.orchestration.incremental.rebuild_decision import RebuildDecision

        if not template_name:
            # Fallback: rebuild all affected pages
            affected = self.cache.get_affected_pages(template_path)
            return RebuildDecision(
                blocks_to_rewarm=set(),
                pages_to_rebuild={Path(p) for p in affected},
                skip_all_pages=False,
                reason="Could not resolve template name",
                child_templates=set(),
            )

        try:
            decision_engine = self._get_decision_engine()
            return decision_engine.decide(template_name, template_path)
        except Exception as e:
            logger.debug(
                "block_level_decision_failed",
                template=template_name,
                error=str(e),
            )
            # Fallback: rebuild all affected pages
            affected = self.cache.get_affected_pages(template_path)
            return RebuildDecision(
                blocks_to_rewarm=set(),
                pages_to_rebuild={Path(p) for p in affected},
                skip_all_pages=False,
                reason=f"Block-level detection failed: {e}",
                child_templates=set(),
            )

    def _rewarm_blocks(self, template_name: str, blocks: set[str]) -> None:
        """Re-warm specific blocks after changes.

        Uses cached engine and context for efficiency.

        Args:
            template_name: Template name (e.g., "base.html")
            blocks: Set of block names to re-warm
        """
        if not self.block_cache or not blocks:
            return

        # Clear old cached blocks
        for block_name in blocks:
            key = f"{template_name}:{block_name}"
            self.block_cache._site_blocks.pop(key, None)

        # Re-warm using cached engine and context
        try:
            engine = self._get_engine()
            site_context = self._get_site_context()

            for block_name in blocks:
                try:
                    template = engine.env.get_template(template_name)
                    html = template.render_block(block_name, site_context)
                    self.block_cache.set(template_name, block_name, html, scope="site")
                    logger.debug(
                        "block_rewarmed",
                        template=template_name,
                        block=block_name,
                        size_bytes=len(html),
                    )
                except Exception as e:
                    logger.debug(
                        "block_rewarm_failed",
                        template=template_name,
                        block=block_name,
                        error=str(e),
                    )
        except Exception as e:
            logger.debug(
                "block_rewarm_engine_failed",
                template=template_name,
                error=str(e),
            )

    def reset(self) -> None:
        """Reset cached state between builds.

        Call this at the end of a build to release resources.
        """
        self._engine = None
        self._decision_engine = None
        self._site_context = None
