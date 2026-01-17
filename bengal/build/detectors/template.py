"""
Template change detection.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.results import ChangeDetectionResult, RebuildReason, RebuildReasonCode
from bengal.build.detectors.base import normalize_source_path, page_key_for_path
from bengal.protocols import has_clear_template_cache
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.build.contracts.protocol import DetectionContext

logger = get_logger(__name__)


class TemplateChangeDetector:
    """Detect template changes and affected pages."""

    def detect(self, ctx: "DetectionContext") -> ChangeDetectionResult:
        template_files = self._collect_template_files(ctx)
        if not template_files:
            return ChangeDetectionResult.empty()

        pages_to_rebuild: set[CacheKey] = set()
        templates_changed: set[CacheKey] = set()
        rebuild_reasons: dict[CacheKey, RebuildReason] = {}
        changed_template_names: list[str] = []

        for template_file in template_files:
            template_key = self._template_key(ctx, template_file)
            if template_key not in ctx.forced_changed and not ctx.cache.is_changed(template_file):
                continue
            templates_changed.add(template_key)

            template_name = self._path_to_template_name(ctx, template_file)
            if template_name:
                changed_template_names.append(template_name)

            affected_pages = ctx.cache.get_affected_pages(template_file)
            for page_path_str in affected_pages:
                page_path = normalize_source_path(ctx.site.root_path, page_path_str)
                page_key = page_key_for_path(ctx.site.root_path, page_path)
                pages_to_rebuild.add(page_key)
                rebuild_reasons.setdefault(
                    page_key,
                    RebuildReason(
                        RebuildReasonCode.TEMPLATE_CHANGED,
                        trigger=str(template_file),
                    ),
                )

        if changed_template_names:
            self._invalidate_engine_cache(ctx, changed_template_names)

        if not pages_to_rebuild and not templates_changed:
            return ChangeDetectionResult.empty()

        return ChangeDetectionResult(
            pages_to_rebuild=frozenset(pages_to_rebuild),
            rebuild_reasons=rebuild_reasons,
            templates_changed=frozenset(templates_changed),
        )

    def _collect_template_files(self, ctx: "DetectionContext") -> list[Path]:
        template_files: list[Path] = []

        theme_templates_dir = self._get_theme_templates_dir(ctx)
        if theme_templates_dir and theme_templates_dir.exists():
            template_files.extend(theme_templates_dir.rglob("*.html"))

        site_templates_dir = ctx.site.root_path / "templates"
        if site_templates_dir.exists():
            template_files.extend(site_templates_dir.rglob("*.html"))

        return template_files

    def _get_theme_templates_dir(self, ctx: "DetectionContext") -> Path | None:
        """Get the templates directory for the current theme."""
        theme = ctx.site.theme
        if not theme or not isinstance(theme, str):
            return None

        site_theme_dir = ctx.site.root_path / "themes" / theme / "templates"
        if site_theme_dir.exists():
            return site_theme_dir

        import bengal

        bengal_dir = Path(bengal.__file__).parent
        bundled_theme_dir = bengal_dir / "themes" / theme / "templates"
        if bundled_theme_dir.exists():
            return bundled_theme_dir

        return None

    def _path_to_template_name(self, ctx: "DetectionContext", template_path: Path) -> str | None:
        """Convert template file path to template name (relative to template dirs)."""
        try:
            site_templates_dir = ctx.site.root_path / "templates"
            if site_templates_dir.exists():
                try:
                    rel_path = template_path.relative_to(site_templates_dir)
                    return str(rel_path.as_posix())
                except ValueError:
                    pass  # Not relative to site templates, try theme

            theme_templates_dir = self._get_theme_templates_dir(ctx)
            if theme_templates_dir and theme_templates_dir.exists():
                try:
                    rel_path = template_path.relative_to(theme_templates_dir)
                    return str(rel_path.as_posix())
                except ValueError:
                    pass  # Not relative to theme templates either
        except OSError as e:
            # File system errors (permission denied, etc.)
            logger.debug(
                "template_name_resolution_failed",
                template_path=str(template_path),
                error=str(e),
            )
        return None

    def _template_key(self, ctx: "DetectionContext", template_path: Path) -> CacheKey:
        """Create a stable key for templates."""
        try:
            rel = template_path.relative_to(ctx.site.root_path)
            return CacheKey(str(rel).replace("\\", "/"))
        except ValueError:
            return CacheKey(str(template_path))

    def _invalidate_engine_cache(self, ctx: "DetectionContext", template_names: list[str]) -> None:
        """Best-effort template engine cache invalidation."""
        try:
            from bengal.rendering.engines import create_engine

            engine = create_engine(ctx.site)
            if has_clear_template_cache(engine):
                engine.clear_template_cache(template_names)
                logger.debug(
                    "template_engine_cache_invalidated",
                    engine=type(engine).__name__,
                    templates=len(template_names),
                )
        except Exception as e:
            logger.debug(
                "template_engine_cache_invalidation_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
