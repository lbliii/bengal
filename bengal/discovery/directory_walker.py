"""
Directory walking for content discovery.

This module handles directory traversal, symlink loop detection, and file
filtering during content discovery. Extracted from content_discovery.py
per RFC: rfc-modularize-large-files.

Classes:
    DirectoryWalker: Walks directories and yields content items.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.section import Section

logger = get_logger(__name__)

# Content file extensions
CONTENT_EXTENSIONS = {".md", ".markdown", ".rst", ".txt"}


class DirectoryWalker:
    """
    Walks directories to discover content files.

    Handles symlink loop detection via inode tracking to prevent infinite
    recursion when symbolic links create circular references.

    Attributes:
        content_dir: Root content directory
        site: Optional Site reference for configuration
        visited_inodes: Set of visited (device, inode) pairs for loop detection

    Example:
        >>> walker = DirectoryWalker(Path("content"), site=site)
        >>> for item, is_file in walker.walk(Path("content/blog")):
        ...     if is_file:
        ...         print(f"Found file: {item}")
    """

    def __init__(self, content_dir: Path, site: Any | None = None):
        """
        Initialize the directory walker.

        Args:
            content_dir: Root content directory
            site: Optional Site reference for versioning config
        """
        self.content_dir = content_dir
        self.site = site
        self.visited_inodes: set[tuple[int, int]] = set()

    def reset(self) -> None:
        """Reset visited inodes for a new discovery pass."""
        self.visited_inodes.clear()

    def is_content_file(self, file_path: Path) -> bool:
        """
        Check if a file is a content file.

        Args:
            file_path: Path to check

        Returns:
            True if it's a content file
        """
        return file_path.suffix.lower() in CONTENT_EXTENSIONS

    def should_skip_item(self, item_path: Path) -> bool:
        """
        Check if an item should be skipped during discovery.

        Skips hidden files and directories except:
        - _index.md and _index.markdown (section index pages)
        - _versions and _shared directories (when versioning is enabled)

        Args:
            item_path: Path to check

        Returns:
            True if item should be skipped
        """
        is_versioning_dir = item_path.name in ("_versions", "_shared") and getattr(
            self.site, "versioning_enabled", False
        )
        return (
            item_path.name.startswith((".", "_"))
            and item_path.name not in ("_index.md", "_index.markdown")
            and not is_versioning_dir
        )

    def is_versioning_infrastructure(self, item_path: Path) -> bool:
        """
        Check if item is versioning infrastructure (_versions, _shared).

        Args:
            item_path: Path to check

        Returns:
            True if this is a versioning directory
        """
        return item_path.name in ("_versions", "_shared") and getattr(
            self.site, "versioning_enabled", False
        )

    def check_symlink_loop(self, directory: Path) -> bool:
        """
        Check if a directory would create a symlink loop.

        Uses inode tracking to detect when a directory has already been
        visited (via symlink or otherwise).

        Args:
            directory: Directory to check

        Returns:
            True if this is a loop (should skip), False if safe to enter
        """
        try:
            stat = directory.stat()
            inode_key = (stat.st_dev, stat.st_ino)

            if inode_key in self.visited_inodes:
                logger.warning(
                    "symlink_loop_detected",
                    path=str(directory),
                    action="skipping_to_prevent_infinite_recursion",
                )
                return True

            self.visited_inodes.add(inode_key)
            return False
        except (OSError, PermissionError) as e:
            logger.warning(
                "directory_stat_failed",
                path=str(directory),
                error=str(e),
                error_type=type(e).__name__,
                action="skipping",
            )
            return True

    def list_directory(self, directory: Path) -> list[Path]:
        """
        List items in a directory, sorted alphabetically.

        Args:
            directory: Directory to list

        Returns:
            Sorted list of paths, or empty list on error
        """
        try:
            return sorted(directory.iterdir())
        except PermissionError as e:
            logger.warning(
                "directory_permission_denied",
                path=str(directory),
                error=str(e),
                action="skipping",
            )
            return []

    def walk_directory(
        self,
        directory: Path,
        parent_section: Section | None = None,
    ) -> Iterator[tuple[Path, bool]]:
        """
        Walk a directory and yield content items.

        Yields tuples of (path, is_file) for each item that should be
        processed. Handles symlink loop detection and item filtering.

        Args:
            directory: Directory to walk
            parent_section: Optional parent section for context

        Yields:
            Tuples of (item_path, is_file)
        """
        if not directory.exists():
            return

        if self.check_symlink_loop(directory):
            return

        for item in self.list_directory(directory):
            if self.should_skip_item(item):
                continue

            if item.is_file() and self.is_content_file(item):
                yield item, True
            elif item.is_dir():
                yield item, False


