"""
LocalSource - Content source for local filesystem.

This is the default source, reading markdown files from a directory.
No external dependencies required.

Performance Optimizations:
- Configurable sorting (disabled by default for O(n) instead of O(n log n))
- Pre-compiled exclude patterns using regex for O(1) matching per file
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import AsyncIterator
from datetime import datetime
from functools import cached_property
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
        from bengal.errors import BengalContentError, ErrorCode, record_error

        # Record but continue - graceful degradation
        error = BengalContentError(
            "Failed to parse frontmatter in content",
            code=ErrorCode.N001,
            suggestion="Check YAML syntax in frontmatter block",
            original_error=e,
        )
        record_error(error)
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
        sort: bool - Sort entries alphabetically (default: False for performance)

    Example:
        >>> source = LocalSource("docs", {
        ...     "directory": "content/docs",
        ...     "glob": "**/*.md",
        ...     "exclude": ["_drafts/*"],
        ...     "sort": True,  # Enable alphabetical ordering
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

        from bengal.errors import BengalConfigError, ErrorCode

        if "directory" not in config:
            raise BengalConfigError(
                f"LocalSource '{name}' requires 'directory' in config",
                suggestion="Add 'directory' to LocalSource configuration",
                code=ErrorCode.C002,
            )

        self.directory = Path(config["directory"])
        self.glob_pattern = config.get("glob", "**/*.md")
        self.exclude_patterns: list[str] = config.get("exclude", [])
        self.sort_entries = config.get("sort", False)

    @cached_property
    def _exclude_regex(self) -> re.Pattern[str] | None:
        """
        Pre-compile exclude patterns to single regex.

        Converts fnmatch glob patterns to a combined regex for O(1) matching
        per file instead of O(p) where p = number of patterns.

        Returns:
            Compiled regex pattern or None if no patterns
        """
        if not self.exclude_patterns:
            return None

        try:
            # Convert fnmatch patterns to regex and combine
            regex_parts = [fnmatch.translate(p) for p in self.exclude_patterns]
            combined = "|".join(f"(?:{p})" for p in regex_parts)
            return re.compile(combined)
        except re.error as e:
            logger.warning(f"Failed to compile exclude patterns: {e}. Using fnmatch fallback.")
            return None

    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        """
        Fetch all content entries from this directory.

        Entries are yielded in filesystem order by default for O(n) performance.
        Set `sort: true` in config for alphabetical ordering (O(n log n)).

        Yields:
            ContentEntry for each matching file
        """
        if not self.directory.exists():
            logger.warning(f"Source directory does not exist: {self.directory}")
            return

        # Get paths - optionally sort for deterministic ordering
        paths = self.directory.glob(self.glob_pattern)
        if self.sort_entries:
            paths = sorted(paths)

        for path in paths:
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
        except FileNotFoundError as e:
            from bengal.errors import BengalContentError, ErrorCode, record_error

            error = BengalContentError(
                f"Content file not found: {path}",
                code=ErrorCode.N004,
                file_path=path,
                suggestion="Verify the file exists and path is correct",
                original_error=e,
            )
            record_error(error, file_path=str(path))
            logger.warning(f"Failed to read {path}: {e}")
            return None
        except UnicodeDecodeError as e:
            from bengal.errors import BengalContentError, ErrorCode, record_error

            error = BengalContentError(
                f"Failed to read content file (encoding error): {path}",
                code=ErrorCode.N003,
                file_path=path,
                suggestion="Check file encoding (UTF-8 expected)",
                original_error=e,
            )
            record_error(error, file_path=str(path))
            logger.warning(f"Failed to read {path}: {e}")
            return None
        except PermissionError as e:
            from bengal.errors import BengalDiscoveryError, ErrorCode, record_error

            error = BengalDiscoveryError(
                f"Permission denied reading file: {path}",
                code=ErrorCode.D007,
                file_path=path,
                suggestion="Check file permissions",
                original_error=e,
            )
            record_error(error, file_path=str(path))
            logger.warning(f"Failed to read {path}: {e}")
            return None
        except Exception as e:
            from bengal.errors import BengalContentError, ErrorCode, record_error

            error = BengalContentError(
                f"Failed to read content file: {path}",
                code=ErrorCode.N003,
                file_path=path,
                suggestion="Check file encoding (UTF-8 expected) and permissions",
                original_error=e,
            )
            record_error(error, file_path=str(path))
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

        Uses pre-compiled regex for O(1) matching when available,
        falls back to fnmatch loop if regex compilation failed.

        Args:
            path: Full path to check

        Returns:
            True if path matches an exclude pattern
        """
        if not self.exclude_patterns:
            return False

        rel_path = str(path.relative_to(self.directory))

        # Use pre-compiled regex if available (O(1) per file)
        if self._exclude_regex is not None:
            return bool(self._exclude_regex.fullmatch(rel_path))

        # Fallback to original fnmatch loop (O(p) per file)
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
