"""
ContentEntry - Unified representation of content from any source.

This is the output of all ContentSource implementations and serves as
the bridge between remote/local content and Bengal's Page model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ContentEntry:
    """
    Unified representation of content from any source.

    ContentEntry is source-agnostic - whether content comes from local files,
    GitHub, Notion, or a REST API, it's represented the same way.

    Attributes:
        id: Unique identifier within the source (e.g., file path, doc ID)
        slug: URL-friendly slug for routing
        content: Raw content (typically markdown)
        frontmatter: Parsed metadata dictionary
        source_type: Type of source ('local', 'github', 'notion', 'rest')
        source_name: Name of the configured source instance
        source_url: Original URL for attribution (optional)
        last_modified: Last modification time (for cache invalidation)
        checksum: Content hash (for change detection)
        etag: HTTP ETag (for conditional requests)
        cached_path: Local cache file path (if cached)
        cached_at: When this entry was cached

    Example:
        >>> entry = ContentEntry(
        ...     id="getting-started.md",
        ...     slug="getting-started",
        ...     content="# Getting Started\\n\\nWelcome to...",
        ...     frontmatter={"title": "Getting Started", "weight": 1},
        ...     source_type="local",
        ...     source_name="docs",
        ... )
        >>> entry.title
        'Getting Started'
    """

    # Identity
    id: str
    slug: str

    # Content
    content: str
    frontmatter: dict[str, Any] = field(default_factory=dict)

    # Source metadata
    source_type: str = "local"
    source_name: str = "default"
    source_url: str | None = None

    # Versioning (for cache invalidation)
    last_modified: datetime | None = None
    checksum: str | None = None
    etag: str | None = None

    # Local cache info
    cached_path: Path | None = None
    cached_at: datetime | None = None

    @property
    def title(self) -> str:
        """Get title from frontmatter or derive from slug."""
        return self.frontmatter.get("title") or self.slug.replace("-", " ").title()

    @property
    def is_remote(self) -> bool:
        """Check if this entry came from a remote source."""
        return self.source_type not in ("local", "filesystem")

    @property
    def is_cached(self) -> bool:
        """Check if this entry has been cached locally."""
        return self.cached_path is not None and self.cached_at is not None

    def to_page_kwargs(self) -> dict[str, Any]:
        """
        Convert to kwargs for Page creation.

        Returns:
            Dictionary of kwargs suitable for Page.__init__
        """
        return {
            "content": self.content,
            "frontmatter": self.frontmatter,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "slug": self.slug,
        }

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation for JSON/cache storage
        """
        return {
            "id": self.id,
            "slug": self.slug,
            "content": self.content,
            "frontmatter": self.frontmatter,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "checksum": self.checksum,
            "etag": self.etag,
            "cached_path": str(self.cached_path) if self.cached_path else None,
            "cached_at": self.cached_at.isoformat() if self.cached_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContentEntry:
        """
        Create ContentEntry from dictionary.

        Args:
            data: Dictionary from to_dict() or cache storage

        Returns:
            ContentEntry instance
        """
        return cls(
            id=data["id"],
            slug=data["slug"],
            content=data["content"],
            frontmatter=data.get("frontmatter", {}),
            source_type=data.get("source_type", "local"),
            source_name=data.get("source_name", "default"),
            source_url=data.get("source_url"),
            last_modified=(
                datetime.fromisoformat(data["last_modified"]) if data.get("last_modified") else None
            ),
            checksum=data.get("checksum"),
            etag=data.get("etag"),
            cached_path=Path(data["cached_path"]) if data.get("cached_path") else None,
            cached_at=(
                datetime.fromisoformat(data["cached_at"]) if data.get("cached_at") else None
            ),
        )
