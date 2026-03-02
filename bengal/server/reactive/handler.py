"""Reactive content handler for content-only edits.

Handles single .md file edits (leaf or section) when only the body changed.
Uses RenderingPipeline to parse, transform, and render the page, then writes
to disk. Skips full build (discovery, provenance, post-process).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from patitas import parse_frontmatter

from bengal.core.output import BuildOutputCollector
from bengal.protocols import SiteLike
from bengal.rendering.pipeline.core import RenderingPipeline

if TYPE_CHECKING:
    from bengal.protocols import PageLike
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


class ReactiveContentHandler:
    """Handles content-only edits via reactive path (parse + re-render + write)."""

    def __init__(self, site: SiteLike, output_dir: Path) -> None:
        """Initialize handler with site and output directory.

        Args:
            site: Site instance (must have been built at least once)
            output_dir: Output directory for rendered HTML
        """
        self.site = site
        self.output_dir = output_dir

    def handle_content_change(self, path: Path) -> Path | None:
        """Process content-only change for a single .md file.

        Flow: find page → read source → update page._raw_content → run
        RenderingPipeline.process_page → write to disk.

        Args:
            path: Path to the changed markdown file (absolute or relative)

        Returns:
            Output path of the rendered page if successful, None otherwise
        """
        page = self._find_page(path)
        if page is None:
            logger.debug("reactive_page_not_found", path=str(path))
            return None

        try:
            raw_file = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("reactive_read_failed", path=str(path), error=str(e))
            return None

        # _raw_content must be body-only (frontmatter stripped); discovery uses
        # ContentParser.parse_file which returns (body, metadata). Passing the
        # full file would render YAML as markdown.
        _, body_content = parse_frontmatter(raw_file)
        page._raw_content = body_content
        page.html_content = None

        # Invalidate content-derived caches so pipeline recomputes
        if hasattr(page, "_plain_text_cache"):
            object.__setattr__(page, "_plain_text_cache", None)
        if hasattr(page, "_html_cache"):
            object.__setattr__(page, "_html_cache", None)
        if hasattr(page, "_ast_cache"):
            object.__setattr__(page, "_ast_cache", None)

        # Use RenderingPipeline for full parse + transform + render + write
        # changed_sources={path} ensures cache bypass (skip_cache=True)
        # output_collector enables hot reload tracking (RFC: content-only-hot-reload)
        output_collector = BuildOutputCollector(output_dir=self.output_dir)
        pipeline = RenderingPipeline(
            self.site,
            quiet=True,
            build_stats=None,
            build_context=None,
            output_collector=output_collector,
            changed_sources={path},
            block_cache=None,
            write_behind=None,
            build_cache=None,
        )
        pipeline.process_page(page)

        return page.output_path if page.output_path else None

    def _find_page(self, path: Path) -> PageLike | None:
        """Find page in site.pages matching the given source path.

        Uses a lazily-built index for O(1) lookup. Index is invalidated
        automatically since ReactiveContentHandler is instantiated fresh
        per trigger.
        """
        if not hasattr(self, "_page_index"):
            self._page_index: dict[Path, PageLike] = {}
            for page in self.site.pages:
                try:
                    self._page_index[Path(page.source_path).resolve()] = page
                except OSError, ValueError, TypeError:
                    continue
        try:
            return self._page_index.get(path.resolve())
        except OSError, ValueError:
            return None
