"""
RESTSource - Content source for REST APIs.

Fetches content from any REST API that returns JSON, with
configurable field mappings for content and frontmatter.

Requires: pip install bengal[rest] (installs aiohttp)
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

try:
    import aiohttp
except ImportError as e:
    raise ImportError("RESTSource requires aiohttp.\nInstall with: pip install bengal[rest]") from e

from bengal.content_layer.entry import ContentEntry
from bengal.content_layer.source import ContentSource
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class RESTSource(ContentSource):
    """
    Content source for REST APIs.

    Fetches content from any REST API that returns JSON. Supports:
    - Custom headers (with environment variable expansion)
    - Configurable field mappings for content and frontmatter
    - Pagination (link header or cursor-based)

    Configuration:
        url: str - API endpoint URL (required)
        headers: dict - Request headers (optional, supports ${ENV_VAR})
        content_field: str - JSON path to content (default: "content")
        id_field: str - JSON path to ID (default: "id")
        frontmatter_fields: dict - Mapping of frontmatter keys to JSON paths
        items_path: str - JSON path to items array (default: auto-detect)
        pagination: dict - Pagination config (optional)
            strategy: str - "link_header" or "cursor"
            cursor_field: str - Field containing next cursor

    Example:
        >>> source = RESTSource("blog", {
        ...     "url": "https://api.example.com/posts",
        ...     "headers": {"Authorization": "Bearer ${API_TOKEN}"},
        ...     "content_field": "body",
        ...     "frontmatter_fields": {
        ...         "title": "title",
        ...         "date": "published_at",
        ...         "tags": "categories",
        ...     },
        ... })
    """

    source_type = "rest"

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        """
        Initialize REST source.

        Args:
            name: Source name
            config: Configuration with 'url' required
        """
        super().__init__(name, config)

        from bengal.errors import BengalConfigError

        if "url" not in config:
            raise BengalConfigError(
                f"RESTSource '{name}' requires 'url' in config",
                suggestion="Add 'url' to RESTSource configuration",
            )

        self.url = config["url"]
        self.content_field = config.get("content_field", "content")
        self.id_field = config.get("id_field", "id")
        self.items_path = config.get("items_path")
        self.frontmatter_mapping: dict[str, str] = config.get("frontmatter_fields", {})
        self.pagination = config.get("pagination")

        # Expand environment variables in headers
        raw_headers = config.get("headers", {})
        self.headers = {k: os.path.expandvars(str(v)) for k, v in raw_headers.items()}

    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        """
        Fetch all content from the API.

        Handles pagination automatically if configured.

        Yields:
            ContentEntry for each item
        """
        async with aiohttp.ClientSession(headers=self.headers) as session:
            url: str | None = self.url

            while url:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

                # Extract items from response
                items = self._extract_items(data)

                for item in items:
                    entry = self._item_to_entry(item)
                    if entry:
                        yield entry

                # Get next page URL
                url = self._get_next_url(data, resp)

    async def fetch_one(self, id: str) -> ContentEntry | None:
        """
        Fetch a single item by ID.

        Args:
            id: Item identifier

        Returns:
            ContentEntry if found, None otherwise
        """
        async with aiohttp.ClientSession(headers=self.headers) as session:
            url = f"{self.url.rstrip('/')}/{id}"

            async with session.get(url) as resp:
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                data = await resp.json()

            return self._item_to_entry(data)

    def _extract_items(self, data: Any) -> list[dict[str, Any]]:
        """
        Extract items array from response.

        Args:
            data: JSON response data

        Returns:
            List of item dictionaries
        """
        # If items_path is specified, use it
        if self.items_path:
            items = self._get_nested(data, self.items_path)
            return items if isinstance(items, list) else []

        # Auto-detect: if response is a list, use it directly
        if isinstance(data, list):
            return data

        # Try common patterns
        for key in ["items", "data", "results", "entries", "posts", "pages"]:
            if key in data and isinstance(data[key], list):
                return list(data[key])

        # Single item response
        if isinstance(data, dict) and self.id_field in data:
            return [data]

        return []

    def _item_to_entry(self, item: dict[str, Any]) -> ContentEntry | None:
        """
        Convert API item to ContentEntry.

        Args:
            item: Item dictionary from API

        Returns:
            ContentEntry or None if content missing
        """
        # Extract content
        content = self._get_nested(item, self.content_field)
        if not content:
            logger.debug(f"Skipping item without content field '{self.content_field}'")
            return None

        # Ensure content is string
        content = str(content)

        # Extract ID
        item_id = self._get_nested(item, self.id_field)
        if item_id is None:
            logger.debug(f"Skipping item without id field '{self.id_field}'")
            return None
        item_id = str(item_id)

        # Extract frontmatter from configured fields
        frontmatter: dict[str, Any] = {}
        for fm_key, json_path in self.frontmatter_mapping.items():
            value = self._get_nested(item, json_path)
            if value is not None:
                frontmatter[fm_key] = value

        # Generate slug
        slug = frontmatter.get("slug") or item_id

        # Source URL
        source_url = item.get("url") or item.get("html_url") or item.get("link")

        return ContentEntry(
            id=item_id,
            slug=str(slug),
            content=content,
            frontmatter=frontmatter,
            source_type=self.source_type,
            source_name=self.name,
            source_url=source_url,
        )

    def _get_nested(self, obj: Any, path: str) -> Any:
        """
        Get nested value by dot-separated path.

        Args:
            obj: Object to traverse
            path: Dot-separated path (e.g., "data.items.0.name")

        Returns:
            Value at path or None
        """
        for key in path.split("."):
            if isinstance(obj, dict):
                obj = obj.get(key)
            elif isinstance(obj, list):
                try:
                    obj = obj[int(key)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return obj

    def _get_next_url(
        self,
        data: dict[str, Any],
        response: aiohttp.ClientResponse,
    ) -> str | None:
        """
        Extract next page URL from response.

        Args:
            data: Response JSON
            response: aiohttp response object

        Returns:
            Next page URL or None
        """
        if not self.pagination:
            return None

        strategy = self.pagination.get("strategy", "link_header")

        if strategy == "link_header":
            # Parse Link header for rel="next"
            link = response.headers.get("Link", "")
            for part in link.split(","):
                if 'rel="next"' in part or "rel=next" in part:
                    url = part.split(";")[0].strip()
                    return url.strip("<>")

        elif strategy == "cursor":
            # Get cursor from response
            cursor_field = self.pagination.get("cursor_field", "next_cursor")
            cursor = self._get_nested(data, cursor_field)
            if cursor:
                # Build URL with cursor
                sep = "&" if "?" in self.url else "?"
                param = self.pagination.get("cursor_param", "cursor")
                return f"{self.url}{sep}{param}={cursor}"

        elif strategy == "offset":
            # Offset-based pagination
            offset_field = self.pagination.get("offset_field", "offset")
            limit_field = self.pagination.get("limit_field", "limit")
            total_field = self.pagination.get("total_field", "total")

            offset = self._get_nested(data, offset_field) or 0
            limit = self._get_nested(data, limit_field) or 20
            total = self._get_nested(data, total_field)

            if total and offset + limit < total:
                sep = "&" if "?" in self.url else "?"
                return f"{self.url}{sep}offset={offset + limit}&limit={limit}"

        return None
