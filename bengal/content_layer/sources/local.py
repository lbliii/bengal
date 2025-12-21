"""
LocalSource - Content source for local filesystem.

This is the default source, reading markdown files from a directory.
No external dependencies required.
"""

from __future__ import annotations

import fnmatch
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any

from bengal.content_layer.entry import ContentEntry
from bengal.content_layer.source import ContentSource
from bengal.utils.hashing import hash_str
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from content.

    Args:
        content: Raw file content with optional frontmatter

    Returns:
        Tuple of (frontmatter dict, body content)
    """
    if not content.startswith("---"):
        return {}, content

    try:
        # Find end of frontmatter
        end_idx = content.find("---", 3)
        if end_idx == -1:
            return {}, content

        frontmatter_str = content[3:end_idx].strip()
        body = content[end_idx + 3 :].strip()

        # Parse YAML
        import yaml

        frontmatter = yaml.safe_load(frontmatter_str) or {}
        return frontmatter, body

    except Exception as e:
        logger.warning(f"Failed to parse frontmatter: {e}")
        return {}, content


class LocalSource(ContentSource):
    """
    Content source for local filesystem.

    Reads markdown files from a directory, parsing frontmatter and
    generating content entries.

    Configuration:
        directory: str - Directory path (relative to site root)
        glob: str - Glob pattern for matching files (default: "**/*.md")
        exclude: list[str] - Patterns to exclude (default: [])

    Example:
        >>> source = LocalSource("docs", {
        ...     "directory": "content/docs",
        ...     "glob": "**/*.md",
        ...     "exclude": ["_drafts/*"],
        ... })
        >>> async for entry in source.fetch_all():
        ...     print(entry.title)
    """

    source_type = "local"

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        """
        Initialize local source.

        Args:
            name: Source name
            config: Configuration with 'directory' key required

        Raises:
            ValueError: If 'directory' not specified
        """
        super().__init__(name, config)

        from bengal.errors import BengalConfigError

        if "directory" not in config:
            raise BengalConfigError(
                f"LocalSource '{name}' requires 'directory' in config",
                suggestion="Add 'directory' to LocalSource configuration",
            )

        self.directory = Path(config["directory"])
        self.glob_pattern = config.get("glob", "**/*.md")
        self.exclude_patterns: list[str] = config.get("exclude", [])

    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        """
        Fetch all content entries from this directory.

        Yields:
            ContentEntry for each matching file
        """
        if not self.directory.exists():
            logger.warning(f"Source directory does not exist: {self.directory}")
            return

        for path in sorted(self.directory.glob(self.glob_pattern)):
            if not path.is_file():
                continue

            if self._should_exclude(path):
                logger.debug(f"Excluded: {path}")
                continue

            entry = await self._load_file(path)
            if entry:
                yield entry

    async def fetch_one(self, id: str) -> ContentEntry | None:
        """
        Fetch a single file by relative path.

        Args:
            id: Relative path from directory (e.g., "getting-started.md")

        Returns:
            ContentEntry if found, None otherwise
        """
        path = self.directory / id

        if not path.exists() or not path.is_file():
            return None

        if self._should_exclude(path):
            return None

        return await self._load_file(path)

    async def _load_file(self, path: Path) -> ContentEntry | None:
        """
        Load a single file into a ContentEntry.

        Args:
            path: Path to the file

        Returns:
            ContentEntry or None if file can't be read
        """
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {path}: {e}")
            return None

        frontmatter, body = _parse_frontmatter(content)

        # Generate checksum
        checksum = hash_str(content, truncate=16)

        # Get file stats
        stat = path.stat()
        last_modified = datetime.fromtimestamp(stat.st_mtime)

        # Generate slug from path
        rel_path = path.relative_to(self.directory)
        slug = self._path_to_slug(rel_path)

        return ContentEntry(
            id=str(rel_path),
            slug=slug,
            content=body,
            frontmatter=frontmatter,
            source_type=self.source_type,
            source_name=self.name,
            source_url=None,
            last_modified=last_modified,
            checksum=checksum,
            cached_path=path,
        )

    def _should_exclude(self, path: Path) -> bool:
        """
        Check if path should be excluded.

        Args:
            path: Full path to check

        Returns:
            True if path matches an exclude pattern
        """
        if not self.exclude_patterns:
            return False

        rel_path = str(path.relative_to(self.directory))

        return any(fnmatch.fnmatch(rel_path, pattern) for pattern in self.exclude_patterns)

    def _path_to_slug(self, rel_path: Path) -> str:
        """
        Convert relative path to URL slug.

        Args:
            rel_path: Path relative to source directory

        Returns:
            URL-friendly slug
        """
        # Remove extension
        slug = str(rel_path.with_suffix(""))

        # Normalize separators
        slug = slug.replace("\\", "/")

        # Handle index files
        if slug.endswith("/index") or slug == "index":
            slug = slug.rsplit("/index", 1)[0] or "index"

        return slug

    async def get_last_modified(self) -> datetime | None:
        """
        Get most recent modification time of any file.

        Returns:
            Most recent mtime or None
        """
        if not self.directory.exists():
            return None

        latest: datetime | None = None

        for path in self.directory.glob(self.glob_pattern):
            if not path.is_file() or self._should_exclude(path):
                continue

            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            if latest is None or mtime > latest:
                latest = mtime

        return latest
