"""
Bengal-specific stream adapters for the reactive dataflow pipeline.

This module bridges the generic pipeline primitives with Bengal's domain:
- ContentDiscoveryStream: Discovers content files
- PageStream: Creates Page objects from parsed content
- RenderStream: Renders pages with templates

These adapters wrap existing Bengal classes (ContentDiscovery, Page, etc.)
making them work with the reactive pipeline infrastructure.

Related:
    - bengal/pipeline/core.py - Base Stream class
    - bengal/pipeline/build.py - Build pipeline factory
    - bengal/discovery/content_discovery.py - Wrapped by ContentDiscoveryStream
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.pipeline.core import Stream, StreamItem, StreamKey
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


@dataclass
class ParsedContent:
    """
    Intermediate representation of parsed content file.

    Bridges ContentDiscovery output with Page creation.

    Attributes:
        source_path: Path to the source file
        content: Raw markdown content (after frontmatter)
        metadata: Frontmatter metadata dict
        content_hash: Hash of file contents for cache invalidation
    """

    source_path: Path
    content: str
    metadata: dict[str, Any]
    content_hash: str


class ContentDiscoveryStream(Stream[ParsedContent]):
    """
    Stream that discovers and parses content files.

    Wraps bengal.discovery.ContentDiscovery to emit ParsedContent items
    that can flow through the pipeline.

    Example:
        >>> stream = ContentDiscoveryStream(content_dir)
        >>> for item in stream.iterate():
        ...     print(item.value.source_path)
    """

    def __init__(
        self,
        content_dir: Path,
        *,
        include_hidden: bool = False,
        extensions: tuple[str, ...] = (".md", ".markdown"),
    ) -> None:
        """
        Initialize content discovery stream.

        Args:
            content_dir: Root directory to discover content in
            include_hidden: Whether to include hidden files/dirs
            extensions: File extensions to include
        """
        super().__init__("content_discovery")
        self._content_dir = content_dir
        self._include_hidden = include_hidden
        self._extensions = extensions

    def _produce(self) -> Iterator[StreamItem[ParsedContent]]:
        """Discover and parse content files."""
        import hashlib

        import frontmatter

        from bengal.utils.file_io import read_text_file

        for file_path in self._discover_files():
            try:
                # Read and hash content
                file_content = read_text_file(file_path)
                content_hash = hashlib.sha256(file_content.encode()).hexdigest()[:16]

                # Parse frontmatter
                try:
                    post = frontmatter.loads(file_content)
                    content = post.content
                    metadata = dict(post.metadata)
                except Exception as e:
                    logger.debug(
                        "frontmatter_parse_failed",
                        file_path=str(file_path),
                        error=str(e),
                    )
                    content = file_content
                    metadata = {
                        "title": file_path.stem.replace("-", " ").replace("_", " ").title(),
                        "_parse_error": str(e),
                    }

                parsed = ParsedContent(
                    source_path=file_path,
                    content=content,
                    metadata=metadata,
                    content_hash=content_hash,
                )

                # Create stream item with path as ID and content hash as version
                yield StreamItem(
                    key=StreamKey(
                        source=self.name,
                        id=str(file_path.relative_to(self._content_dir)),
                        version=content_hash,
                    ),
                    value=parsed,
                )

            except Exception as e:
                logger.warning(
                    "content_discovery_error",
                    file_path=str(file_path),
                    error=str(e),
                )
                continue

    def _discover_files(self) -> Iterator[Path]:
        """Walk content directory and yield matching files."""
        seen_inodes: set[int] = set()

        def walk(directory: Path) -> Iterator[Path]:
            try:
                entries = sorted(directory.iterdir())
            except PermissionError:
                logger.debug("permission_denied", path=str(directory))
                return

            for entry in entries:
                # Skip hidden unless explicitly included
                if not self._include_hidden and entry.name.startswith("."):
                    continue

                # Skip _index.md's parent check but include _index.md itself
                if entry.name.startswith("_") and entry.name != "_index.md":
                    continue

                if entry.is_symlink():
                    # Check for symlink loops
                    try:
                        inode = entry.stat().st_ino
                        if inode in seen_inodes:
                            logger.debug("symlink_loop_detected", path=str(entry))
                            continue
                        seen_inodes.add(inode)
                    except OSError:
                        continue

                if entry.is_dir():
                    yield from walk(entry)
                elif entry.is_file() and entry.suffix in self._extensions:
                    yield entry

        yield from walk(self._content_dir)


def create_content_stream(
    site: Site,
    *,
    use_collections: bool = True,
) -> Stream[ParsedContent]:
    """
    Create a content discovery stream for a site.

    Factory function that creates a properly configured ContentDiscoveryStream.

    Args:
        site: Bengal Site instance
        use_collections: Whether to validate against collection schemas

    Returns:
        Stream of ParsedContent items
    """
    content_dir = site.root_path / "content"
    return ContentDiscoveryStream(content_dir)


def create_page_stream(
    content_stream: Stream[ParsedContent],
    site: Site,
) -> Stream[Page]:
    """
    Create a stream that transforms ParsedContent into Page objects.

    Args:
        content_stream: Upstream stream of ParsedContent
        site: Bengal Site instance for Page creation

    Returns:
        Stream of Page objects
    """
    from bengal.core.page import Page

    def create_page(parsed: ParsedContent) -> Page:
        """Transform ParsedContent into Page."""
        return Page(
            source_path=parsed.source_path,
            content=parsed.content,
            metadata=parsed.metadata,
            _site=site,
        )

    return content_stream.map(create_page, name="create_page")


@dataclass
class RenderedPage:
    """
    A page that has been rendered to HTML.

    Attributes:
        page: Original Page object
        html: Rendered HTML content
        output_path: Relative path for output file
    """

    page: Page
    html: str
    output_path: Path


def create_render_stream(
    page_stream: Stream[Page],
    site: Site,
    navigation: Any = None,
) -> Stream[RenderedPage]:
    """
    Create a stream that renders Page objects to HTML.

    Args:
        page_stream: Upstream stream of Page objects
        site: Bengal Site instance
        navigation: Pre-built navigation (if available)

    Returns:
        Stream of RenderedPage objects
    """

    def render_page(page: Page) -> RenderedPage:
        """Render a single page."""
        from bengal.rendering.template_engine import TemplateEngine

        # Get or create template engine
        engine = getattr(site, "_template_engine", None)
        if engine is None:
            engine = TemplateEngine(site)
            site._template_engine = engine

        try:
            # Render page with template
            html = engine.render_page(page, navigation=navigation)

            # Compute output path
            output_path = page.url.lstrip("/")
            if not output_path.endswith(".html"):
                output_path = output_path.rstrip("/") + "/index.html"

            return RenderedPage(
                page=page,
                html=html,
                output_path=Path(output_path),
            )
        except Exception as e:
            logger.error(
                "render_failed",
                page=str(page.source_path),
                error=str(e),
            )
            raise

    return page_stream.map(render_page, name="render_page")


def write_output(site: Site, rendered: RenderedPage) -> None:
    """
    Write rendered page to disk.

    Args:
        site: Bengal Site instance
        rendered: RenderedPage to write
    """
    output_path = site.output_dir / rendered.output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered.html, encoding="utf-8")
    logger.debug("wrote_page", path=str(rendered.output_path))


class FileChangeStream(Stream[Path]):
    """
    Stream that emits changed files for incremental builds.

    Used by the dev server and watch mode to emit files that have changed
    since the last build.

    Example:
        >>> stream = FileChangeStream(changed_paths)
        >>> for item in stream.iterate():
        ...     print(f"Changed: {item.value}")
    """

    def __init__(self, changed_files: list[Path]) -> None:
        """
        Initialize file change stream.

        Args:
            changed_files: List of paths that have changed
        """
        super().__init__("file_changes")
        self._changed_files = changed_files

    def _produce(self) -> Iterator[StreamItem[Path]]:
        """Emit changed file paths."""
        import hashlib
        import time

        timestamp = str(time.time())

        for file_path in self._changed_files:
            # Use file path as ID, timestamp as version (always fresh)
            version = hashlib.sha256(f"{file_path}:{timestamp}".encode()).hexdigest()[:16]

            yield StreamItem(
                key=StreamKey(
                    source=self.name,
                    id=str(file_path),
                    version=version,
                ),
                value=file_path,
            )
