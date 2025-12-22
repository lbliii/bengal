---
title: Custom Content Sources
description: Fetch content from APIs, databases, or remote services
weight: 50
---

Content sources let Bengal fetch content from anywhere—local files, GitHub repositories, REST APIs, Notion databases, or custom backends. You can create custom sources by implementing the `ContentSource` abstract class.

## Built-in Sources

Bengal includes four content source types:

| Source | Type ID | Use Case |
|--------|---------|----------|
| LocalSource | `local`, `filesystem` | Local markdown files (default) |
| GitHubSource | `github` | GitHub repository content |
| RESTSource | `rest`, `api` | REST API endpoints |
| NotionSource | `notion` | Notion database pages |

## Using Built-in Sources

### Local Source (Default)

The default source for local markdown files:

```python
# collections.py
from bengal.collections import define_collection
from bengal.content_layer import local_loader

collections = {
    "docs": define_collection(
        schema=Doc,
        loader=local_loader("content/docs", exclude=["_drafts/*"]),
    ),
}
```

### GitHub Source

Fetch content from a GitHub repository:

```python
from bengal.content_layer import github_loader

collections = {
    "api-docs": define_collection(
        schema=APIDoc,
        loader=github_loader(
            repo="myorg/api-docs",
            branch="main",
            path="docs/",
            token=os.environ.get("GITHUB_TOKEN"),
        ),
    ),
}
```

Requires: `pip install bengal[github]`

### REST Source

Fetch content from a REST API:

```python
from bengal.content_layer import rest_loader

collections = {
    "posts": define_collection(
        schema=BlogPost,
        loader=rest_loader(
            base_url="https://api.example.com",
            endpoint="/posts",
            auth_header="Bearer ${API_TOKEN}",
        ),
    ),
}
```

Requires: `pip install bengal[github]` (uses aiohttp)

### Notion Source

Fetch pages from a Notion database:

```python
from bengal.content_layer import notion_loader

collections = {
    "wiki": define_collection(
        schema=WikiPage,
        loader=notion_loader(
            database_id="abc123...",
            token=os.environ.get("NOTION_TOKEN"),
        ),
    ),
}
```

Requires: `pip install bengal[notion]`

## Creating a Custom Source

Implement the `ContentSource` abstract class:

```python
from bengal.content_layer.source import ContentSource
from bengal.content_layer.entry import ContentEntry

class MyAPISource(ContentSource):
    """Fetch content from a custom API."""

    @property
    def source_type(self) -> str:
        return "my-api"

    async def fetch_all(self):
        """Fetch all content entries."""
        # Get items from your data source
        items = await self._fetch_items()

        for item in items:
            yield ContentEntry(
                id=item["id"],
                source=self.name,
                source_type=self.source_type,
                path=f"{item['slug']}.md",
                content=item["body"],
                frontmatter={
                    "title": item["title"],
                    "date": item["created_at"],
                },
            )

    async def fetch_one(self, id: str):
        """Fetch a single entry by ID."""
        item = await self._fetch_item(id)
        if not item:
            return None

        return ContentEntry(
            id=item["id"],
            source=self.name,
            source_type=self.source_type,
            path=f"{item['slug']}.md",
            content=item["body"],
            frontmatter={
                "title": item["title"],
                "date": item["created_at"],
            },
        )

    async def _fetch_items(self):
        """Your API call implementation."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(self.config["api_url"]) as resp:
                return await resp.json()

    async def _fetch_item(self, id: str):
        """Fetch single item."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            url = f"{self.config['api_url']}/{id}"
            async with session.get(url) as resp:
                if resp.status == 404:
                    return None
                return await resp.json()
```

## ContentEntry Structure

Each source yields `ContentEntry` objects:

```python
@dataclass
class ContentEntry:
    id: str              # Unique identifier
    source: str          # Source instance name
    source_type: str     # Source type (e.g., "github", "notion")
    path: str            # Virtual file path
    content: str         # Markdown content body
    frontmatter: dict    # Metadata dictionary
    checksum: str | None # Content hash for caching
```

## Registering Custom Sources

### Option 1: Direct Registration

Register your source instance directly:

```python
from bengal.content_layer import ContentLayerManager

manager = ContentLayerManager()
manager.register_custom_source("my-content", MyAPISource(
    name="my-content",
    config={"api_url": "https://api.example.com/content"},
))
```

### Option 2: With Collections

Use your source as a collection loader:

```python
# collections.py
from bengal.collections import define_collection

my_source = MyAPISource(
    name="my-content",
    config={"api_url": "https://api.example.com/content"},
)

collections = {
    "external": define_collection(
        schema=ExternalContent,
        loader=my_source,
    ),
}
```

## Caching

Content sources support caching to avoid redundant fetches:

```python
class MyAPISource(ContentSource):
    # ...

    def get_cache_key(self) -> str:
        """Generate cache key for this source configuration."""
        # Default implementation hashes config
        # Override for custom cache key logic
        return super().get_cache_key()

    async def is_changed(self, cached_checksum: str | None) -> bool:
        """Check if source content has changed."""
        # Return True to force refetch
        # Return False if content is unchanged
        current = await self._get_current_checksum()
        return current != cached_checksum

    async def get_last_modified(self):
        """Return last modification time for cache invalidation."""
        # Return datetime or None
        return None
```

## Sync Wrappers

For convenience, `ContentSource` provides sync wrappers:

```python
# Async (preferred for performance)
async for entry in source.fetch_all():
    process(entry)

# Sync (convenience wrapper)
for entry in source.fetch_all_sync():
    process(entry)

# Single entry
entry = source.fetch_one_sync("my-id")
```

## Error Handling

Handle errors gracefully in your source:

```python
async def fetch_all(self):
    try:
        items = await self._fetch_items()
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch from {self.config['api_url']}: {e}")
        return  # Yield nothing on error

    for item in items:
        try:
            yield self._to_entry(item)
        except KeyError as e:
            logger.warning(f"Skipping malformed item {item.get('id')}: {e}")
            continue
```

## Testing Custom Sources

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_api_source():
    source = MyAPISource(
        name="test",
        config={"api_url": "https://api.example.com"},
    )

    with patch.object(source, "_fetch_items", new_callable=AsyncMock) as mock:
        mock.return_value = [
            {"id": "1", "slug": "test", "title": "Test", "body": "Content", "created_at": "2025-01-01"},
        ]

        entries = [entry async for entry in source.fetch_all()]

        assert len(entries) == 1
        assert entries[0].frontmatter["title"] == "Test"
```

## Related

- [Content Collections](/docs/extending/collections/) for schema validation
- [Build Pipeline](/docs/reference/architecture/core/pipeline/) for understanding discovery phase
