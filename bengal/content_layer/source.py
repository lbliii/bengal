"""
ContentSource - Abstract base class for content sources.

Defines the protocol that all content sources must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.utils.hashing import hash_str

if TYPE_CHECKING:
    from bengal.content_layer.entry import ContentEntry


class ContentSource(ABC):
    """
    Abstract base class for content sources.

    Implementations fetch content from various origins (local files,
    remote APIs, databases) and return unified ContentEntry objects.

    Subclasses must implement:
        - source_type property
        - fetch_all() async generator
        - fetch_one() async method

    Example:
        >>> class MySource(ContentSource):
        ...     source_type = "my-api"
        ...
        ...     async def fetch_all(self):
        ...         for item in await self._fetch_items():
        ...             yield self._to_entry(item)
        ...
        ...     async def fetch_one(self, id: str):
        ...         item = await self._fetch_item(id)
        ...         return self._to_entry(item) if item else None
    """

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        """
        Initialize content source.

        Args:
            name: Unique name for this source instance (e.g., "api-docs")
            config: Source-specific configuration dictionary
        """
        self.name = name
        self.config = config

    @property
    @abstractmethod
    def source_type(self) -> str:
        """
        Return source type identifier.

        Returns:
            String identifier like 'local', 'github', 'notion', 'rest'
        """
        ...

    @abstractmethod
    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        """
        Fetch all content entries from this source.

        Yields:
            ContentEntry for each piece of content

        Example:
            >>> async for entry in source.fetch_all():
            ...     print(entry.title)
        """
        ...
        # Make this a generator
        yield  # type: ignore  # pragma: no cover

    @abstractmethod
    async def fetch_one(self, id: str) -> ContentEntry | None:
        """
        Fetch a single content entry by ID.

        Args:
            id: Source-specific identifier (e.g., file path, doc ID)

        Returns:
            ContentEntry if found, None otherwise
        """
        ...

    def get_cache_key(self) -> str:
        """
        Generate cache key for this source configuration.

        Used to invalidate cache when config changes. Override for
        custom cache key logic.

        Returns:
            16-character hex string based on config hash
        """
        # Sort config items for deterministic hashing
        config_str = f"{self.source_type}:{self.name}:{sorted(self.config.items())}"
        return hash_str(config_str, truncate=16)

    async def get_last_modified(self) -> datetime | None:
        """
        Get last modification time for the entire source.

        Used for cache invalidation. Returns None if unknown or not supported.

        Returns:
            Last modification datetime or None
        """
        return None

    async def is_changed(self, cached_checksum: str | None) -> bool:
        """
        Check if source content has changed since last fetch.

        Args:
            cached_checksum: Previously cached checksum

        Returns:
            True if content may have changed, False if definitely unchanged
        """
        # Default: assume changed (conservative)
        return True

    # =========================================================================
    # Sync convenience methods (wrap async)
    # =========================================================================

    def fetch_all_sync(self) -> Iterator[ContentEntry]:
        """
        Synchronous wrapper for fetch_all().

        Runs the async generator in a new event loop.

        Yields:
            ContentEntry for each piece of content
        """
        from bengal.utils.async_compat import run_async

        async def collect() -> list[ContentEntry]:
            return [entry async for entry in self.fetch_all()]

        entries = run_async(collect())
        yield from entries

    def fetch_one_sync(self, id: str) -> ContentEntry | None:
        """
        Synchronous wrapper for fetch_one().

        Args:
            id: Source-specific identifier

        Returns:
            ContentEntry if found, None otherwise
        """
        from bengal.utils.async_compat import run_async

        return run_async(self.fetch_one(id))

    # =========================================================================
    # Utility methods
    # =========================================================================

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, type={self.source_type!r})"
