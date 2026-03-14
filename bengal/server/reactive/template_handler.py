"""Reactive template handler for template-only edits.

When templates (.html) change, re-renders only affected pages instead of
full discovery + provenance + build. Uses BuildCache.get_affected_pages()
for O(1) reverse dependency lookup.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.core.output import BuildOutputCollector
from bengal.protocols import SiteLike
from bengal.rendering.pipeline.core import RenderingPipeline

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.protocols import PageLike

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

# Max affected pages for reactive template path (above this, full build is faster)
REACTIVE_TEMPLATE_PAGE_THRESHOLD = 50


@dataclass(frozen=True, slots=True)
class TemplateReactiveResult:
    """Result of reactive template re-render."""

    changed_output_paths: tuple[Path, ...]


class ReactiveTemplateHandler:
    """Re-renders only pages affected by template changes."""

    def __init__(
        self,
        site: SiteLike,
        output_dir: Path,
        cache: BuildCache,
    ) -> None:
        """Initialize handler.

        Args:
            site: Site instance (must have been built at least once)
            output_dir: Output directory for rendered HTML
            cache: BuildCache with populated reverse_dependencies
        """
        self.site = site
        self.output_dir = output_dir
        self.cache = cache

    def handle_template_changes(
        self,
        changed_template_paths: set[Path],
    ) -> TemplateReactiveResult | None:
        """Re-render pages affected by template changes.

        Skips discovery, provenance, postprocess. Returns changed output
        paths for reload decision.

        Args:
            changed_template_paths: Set of changed template file paths

        Returns:
            TemplateReactiveResult with changed output paths, or None on failure
        """
        affected_keys: set[str] = set()
        for template_path in changed_template_paths:
            with suppress(Exception):
                affected_keys.update(self.cache.get_affected_pages(template_path))

        if not affected_keys:
            logger.debug(
                "reactive_template_no_affected",
                templates=[str(p) for p in changed_template_paths],
            )
            return None

        if len(affected_keys) > REACTIVE_TEMPLATE_PAGE_THRESHOLD:
            logger.debug(
                "reactive_template_too_many_affected",
                count=len(affected_keys),
                threshold=REACTIVE_TEMPLATE_PAGE_THRESHOLD,
            )
            return None

        root = self.site.root_path or Path.cwd()
        page_index = self._build_page_index()

        pages_to_render: list[PageLike] = []
        for key in affected_keys:
            # Cache keys are content_key format (e.g. "content/about.md")
            # or absolute when site_root was None
            try:
                path = (root / key) if not key.startswith("/") else Path(key)
                resolved = path.resolve()
            except TypeError, ValueError, OSError:
                continue
            page = page_index.get(resolved)
            if page is not None:
                # Skip virtual pages (autodoc, taxonomy, CLI)
                if getattr(page, "is_virtual", False):
                    logger.debug(
                        "reactive_template_skips_virtual",
                        key=key,
                    )
                    return None
                pages_to_render.append(page)

        if not pages_to_render:
            logger.debug(
                "reactive_template_no_pages_found",
                keys=list(affected_keys)[:5],
            )
            return None

        output_collector = BuildOutputCollector(output_dir=self.output_dir)
        pipeline = RenderingPipeline(
            self.site,
            quiet=True,
            build_stats=None,
            build_context=None,
            output_collector=output_collector,
            changed_sources=changed_template_paths,
            block_cache=None,
            write_behind=None,
            build_cache=self.cache,
        )

        changed_outputs: list[Path] = []
        for page in pages_to_render:
            try:
                pipeline.process_page(page)
                if page.output_path:
                    changed_outputs.append(page.output_path)
            except Exception as e:
                logger.warning(
                    "reactive_template_page_failed",
                    page=str(getattr(page, "source_path", page)),
                    error=str(e),
                )
                return None

        return TemplateReactiveResult(changed_output_paths=tuple(changed_outputs))

    def _build_page_index(self) -> dict[Path, PageLike]:
        """Build index from resolved source path to page."""
        index: dict[Path, PageLike] = {}
        for page in self.site.pages:
            try:
                src = getattr(page, "source_path", None)
                if src is None:
                    continue
                path = Path(src) if not isinstance(src, Path) else src
                index[path.resolve()] = page
            except OSError, ValueError, TypeError:
                continue
        return index
