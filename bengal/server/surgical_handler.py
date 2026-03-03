"""Surgical rebuild handler for Tier 2 (frontmatter) and Tier 3a (cascade) edits.

Handles single-page frontmatter changes and _index.md cascade changes without
full prepare_for_rebuild. Patches pages in-place and re-renders only affected
outputs.

Related:
- bengal/server/change_classifier: Classifies changes into tiers
- bengal/server/build_trigger: Routes to this handler for FRONTMATTER/CASCADE
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

from patitas import parse_frontmatter

from bengal.core.output import BuildOutputCollector
from bengal.protocols import SiteLike
from bengal.rendering.pipeline.core import RenderingPipeline
from bengal.server.change_classifier import RebuildScope

if TYPE_CHECKING:
    from bengal.protocols import PageLike

logger = get_logger(__name__)


def _build_page_index(site: SiteLike) -> dict[Path, PageLike]:
    """Build O(1) page lookup by source path."""
    index: dict[Path, PageLike] = {}
    for page in site.pages:
        try:
            src = getattr(page, "source_path", None)
            if src is None:
                continue
            path = Path(src) if not isinstance(src, Path) else src
            index[path.resolve()] = page
        except (OSError, ValueError, TypeError):
            continue
    return index


class SurgicalRebuildHandler:
    """Handles Tier 2 (frontmatter) and Tier 3a (cascade) rebuilds."""

    def __init__(self, site: SiteLike, output_dir: Path) -> None:
        self.site = site
        self.output_dir = output_dir

    def handle_frontmatter_change(
        self,
        path: Path,
        scope: RebuildScope,
        page_index: dict[Path, PageLike],
    ) -> list[Path]:
        """
        Patch page, re-render it + any affected pages.

        Returns list of output paths (relative to output_dir) for reload notification.
        """
        page = page_index.get(path.resolve())
        if page is None:
            logger.debug("surgical_page_not_found", path=str(path))
            return []

        # FULL_REBUILD_KEYS or tags_changed -> caller should use full rebuild
        if scope.tier == "full":
            return []
        if scope.tags_changed:
            # Taxonomy update requires full taxonomy rebuild; fall back to full
            logger.debug("surgical_tags_change_fallback", path=str(path))
            return []

        try:
            raw_file = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("surgical_read_failed", path=str(path), error=str(e))
            return []

        metadata, body_content = parse_frontmatter(raw_file)
        if metadata is None:
            metadata = {}

        # Patch the page (updates metadata, content, invalidates caches)
        if hasattr(page, "patch"):
            page.patch(metadata, body_content)
        else:
            logger.warning("surgical_page_no_patch", path=str(path))
            return []

        # Determine affected pages to re-render
        to_render: list[PageLike] = [page]

        if scope.nav_dirty:
            section_index = self._get_section_index_page(page)
            if section_index is not None and section_index not in to_render:
                to_render.append(section_index)

        return self._render_pages(to_render, path)

    def handle_cascade_change(
        self,
        path: Path,
        page_index: dict[Path, PageLike],
    ) -> list[Path]:
        """
        Rebuild cascade for subtree, re-render affected pages.

        Returns list of output paths for reload notification.
        """
        # Patch _index.md page from disk so cascade snapshot sees new values
        index_page = page_index.get(path.resolve())
        if index_page is not None:
            try:
                raw_file = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                pass
            else:
                metadata, body_content = parse_frontmatter(raw_file)
                if metadata is not None and hasattr(index_page, "patch"):
                    index_page.patch(metadata, body_content)

        # Rebuild cascade snapshot (site.build_cascade_snapshot)
        self.site.build_cascade_snapshot()

        # Find section for this _index.md
        section = self._get_section_for_index_path(path)
        if section is None:
            logger.debug("surgical_cascade_section_not_found", path=str(path))
            return []

        # Collect all pages in this section subtree
        pages_to_render = list(section.get_all_pages(recursive=True))

        return self._render_pages(pages_to_render, path)

    def _get_section_index_page(self, page: PageLike) -> PageLike | None:
        """Get the section index page for a page (the _index.md of its section)."""
        section = getattr(page, "_section", None)
        if section is None:
            return None
        index_page = getattr(section, "index_page", None)
        return index_page

    def _get_section_for_index_path(self, path: Path) -> Any | None:
        """Find the Section whose _index.md is at path."""
        for section in self.site.sections:
            found = self._find_section_with_index(section, path)
            if found is not None:
                return found
        return None

    def _find_section_with_index(self, section: Any, path: Path) -> Any | None:
        """Recursively find section whose index_page.source_path matches path."""
        index_page = getattr(section, "index_page", None)
        if index_page is not None:
            src = getattr(index_page, "source_path", None)
            if src is not None:
                try:
                    if Path(src).resolve() == path.resolve():
                        return section
                except (OSError, ValueError):
                    pass
        for sub in getattr(section, "subsections", []) or []:
            found = self._find_section_with_index(sub, path)
            if found is not None:
                return found
        return None

    def _render_pages(
        self,
        pages: list[PageLike],
        changed_source: Path,
    ) -> list[Path]:
        """Re-render pages via RenderingPipeline, return output paths."""
        if not pages:
            return []

        output_collector = BuildOutputCollector(output_dir=self.output_dir)
        pipeline = RenderingPipeline(
            self.site,
            quiet=True,
            build_stats=None,
            build_context=None,
            output_collector=output_collector,
            changed_sources={changed_source},
            block_cache=None,
            write_behind=None,
            build_cache=None,
        )

        output_paths: list[Path] = []
        for page in pages:
            try:
                pipeline.process_page(page)
                op = getattr(page, "output_path", None)
                if op is not None:
                    if op.is_absolute() and self.output_dir:
                        try:
                            rel = op.relative_to(self.output_dir)
                            output_paths.append(rel)
                        except ValueError:
                            output_paths.append(op)
                    else:
                        output_paths.append(op)
            except Exception as e:
                logger.warning(
                    "surgical_render_failed",
                    page=str(getattr(page, "source_path", "?")),
                    error=str(e),
                )

        return output_paths
