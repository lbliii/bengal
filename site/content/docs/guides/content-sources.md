---
title: Remote Content Sources
weight: 51
description: Fetch content from GitHub, Notion, REST APIs, and more
---

## Do I Need This?

No. By default, Bengal reads content from local files. That works for most sites.

**Use remote sources when:**

- Your docs live in multiple GitHub repos
- Content lives in a CMS (Notion, Contentful, etc.)
- You want to pull API docs from a separate service
- You need to aggregate content from different teams

## Quick Start

Install the loader you need:

```bash
pip install bengal[github]   # GitHub repositories
pip install bengal[notion]   # Notion databases
pip install bengal[rest]     # REST APIs
pip install bengal[all-sources]  # Everything
```

Update your `collections.py`:

```python
from bengal.collections import define_collection, DocPage
from bengal.content_layer import github_loader

collections = {
    # Local content (default)
    "docs": define_collection(
        schema=DocPage,
        directory="content/docs",
    ),

    # Remote content from GitHub
    "api-docs": define_collection(
        schema=DocPage,
        loader=github_loader(
            repo="myorg/api-docs",
            path="docs/",
        ),
    ),
}
```

Build as normal. Remote content is fetched, cached, and validated like local content.

## Available Loaders

### GitHub

Fetch markdown from any GitHub repository:

```python
from bengal.content_layer import github_loader

loader = github_loader(
    repo="owner/repo",       # Required: "owner/repo" format
    branch="main",           # Default: "main"
    path="docs/",            # Default: "" (root)
    token=None,              # Default: uses GITHUB_TOKEN env var
)
```

For private repos, set `GITHUB_TOKEN` environment variable or pass `token` directly.

### Notion

Fetch pages from a Notion database:

```python
from bengal.content_layer import notion_loader

loader = notion_loader(
    database_id="abc123...",  # Required: database ID from URL
    token=None,               # Default: uses NOTION_TOKEN env var
    property_mapping={        # Map Notion properties to frontmatter
        "title": "Name",
        "date": "Published",
        "tags": "Tags",
    },
)
```

**Setup:**
1. Create integration at [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Share your database with the integration
3. Set `NOTION_TOKEN` environment variable

### REST API

Fetch from any JSON API:

```python
from bengal.content_layer import rest_loader

loader = rest_loader(
    url="https://api.example.com/posts",
    headers={"Authorization": "Bearer ${API_TOKEN}"},  # Env vars expanded
    content_field="body",           # JSON path to content
    id_field="id",                  # JSON path to ID
    frontmatter_fields={            # Map API fields to frontmatter
        "title": "title",
        "date": "published_at",
        "tags": "categories",
    },
)
```

### Local (Explicit)

For consistency, you can also use an explicit local loader:

```python
from bengal.content_layer import local_loader

loader = local_loader(
    directory="content/docs",
    glob="**/*.md",
    exclude=["_drafts/*"],
)
```

## Caching

Remote content is cached locally to avoid repeated API calls:

```bash
# Check cache status
bengal sources status

# Force refresh from remote
bengal sources fetch --force

# Clear all cached content
bengal sources clear
```

**Cache behavior:**
- Default TTL: 1 hour
- Cache directory: `.bengal/content_cache/`
- Automatic invalidation when config changes
- Falls back to cache if remote unavailable

## CLI Commands

```bash
# List configured content sources
bengal sources list

# Show cache status (age, size, validity)
bengal sources status

# Fetch/refresh from remote sources
bengal sources fetch
bengal sources fetch --source api-docs  # Specific source
bengal sources fetch --force            # Ignore cache

# Clear cached content
bengal sources clear
bengal sources clear --source api-docs
```

## Environment Variables

| Variable | Used By | Description |
|----------|---------|-------------|
| `GITHUB_TOKEN` | GitHub loader | Personal access token for private repos |
| `NOTION_TOKEN` | Notion loader | Integration token |
| Custom | REST loader | Any `${VAR}` in headers is expanded |

## Multi-Repo Documentation

A common pattern for large organizations:

```python
from bengal.collections import define_collection, DocPage
from bengal.content_layer import github_loader, local_loader

collections = {
    # Main docs (local)
    "docs": define_collection(
        schema=DocPage,
        directory="content/docs",
    ),

    # API reference (from API team's repo)
    "api": define_collection(
        schema=DocPage,
        loader=github_loader(repo="myorg/api-service", path="docs/"),
    ),

    # SDK docs (from SDK repo)
    "sdk": define_collection(
        schema=DocPage,
        loader=github_loader(repo="myorg/sdk", path="docs/"),
    ),
}
```

## Offline Mode

For CI/CD or air-gapped environments:

```python
from bengal.content_layer import ContentLayerManager

manager = ContentLayerManager(
    cache_dir=Path(".bengal/content_cache"),
    offline=True,  # Only use cached content
)
```

In offline mode, builds use cached content only. Fails if cache is empty.

## Custom Loaders

Implement `ContentSource` for any content origin:

```python
from bengal.content_layer import ContentSource, ContentEntry

class MyCustomSource(ContentSource):
    source_type = "my-api"

    async def fetch_all(self):
        for item in await self._get_items():
            yield ContentEntry(
                id=item["id"],
                slug=item["slug"],
                content=item["body"],
                frontmatter={"title": item["title"]},
                source_type=self.source_type,
                source_name=self.name,
            )

    async def fetch_one(self, id: str):
        item = await self._get_item(id)
        if not item:
            return None
        return ContentEntry(...)
```

## Zero-Cost Design

**If you don't use remote sources:**
- No extra dependencies installed
- No network calls
- No import overhead
- No configuration needed

Remote loaders are lazy-loaded only when you import them.

## See Also

- [Content Collections](/docs/guides/content-collections/) — Schema validation for any source
