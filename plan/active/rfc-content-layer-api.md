# RFC: Content Layer API

**Status**: Draft  
**Created**: 2025-12-02  
**Author**: AI Assistant  
**Priority**: High  
**Confidence**: 88% 🟢  
**Est. Impact**: Unified content abstraction, CMS integration, remote content sources

---

## Executive Summary

This RFC proposes a **Content Layer API** that provides a unified abstraction for accessing content from any source - local files, CMSs, databases, APIs, or remote repositories. Content from different sources is accessed through the same interface, enabling hybrid documentation sites that combine local and remote content.

**Key Changes**:
1. Abstract `ContentSource` interface for all content origins
2. Built-in sources: Local, GitHub, REST API, Notion
3. Content caching with smart invalidation
4. Unified query API across all sources
5. Integration with Content Collections (RFC-Content-Collections)

---

## Problem Statement

### Current State

Bengal only supports local filesystem content:

```python
# bengal/discovery/content_discovery.py
class ContentDiscovery:
    """Discovers content from local filesystem only."""

    def discover_content(self, content_dir: Path) -> list[Page]:
        """Walk filesystem and create pages."""
        for path in content_dir.glob("**/*.md"):
            yield self._create_page(path)
```

**Evidence**: `bengal/discovery/content_discovery.py:45-60`

### Pain Points

1. **CMS Integration Barrier**: Teams using Contentful, Sanity, Notion, or Strapi must export content to files or build custom integrations.

2. **Multi-Repo Documentation**: Large organizations have docs spread across multiple repositories. Currently requires manual aggregation.

3. **API Documentation Sync**: API docs generated from OpenAPI specs in separate services can't be directly consumed.

4. **Translation Services**: Content from translation services (Crowdin, Lokalise) requires export/import cycles.

5. **Database-Driven Content**: Dynamic content (user-generated, product catalogs) can't be rendered at build time.

### User Impact

- **Enterprise teams**: Can't integrate existing CMS workflows with Bengal
- **Open source projects**: Struggle to aggregate docs from multiple repos
- **API teams**: Must manually sync OpenAPI specs with documentation
- **Localization teams**: Complex workflows for translated content

### Evidence from Modern SSGs

**Astro Content Layer** (2024):
```typescript
// astro.config.mjs
import { defineConfig } from 'astro';

export default defineConfig({
  experimental: {
    contentLayer: true,
  },
});

// content/config.ts
const blog = defineCollection({
  loader: githubLoader({ repo: 'org/blog-content' }),
  schema: blogSchema,
});
```

**Gatsby** pioneered this with GraphQL data layer (source plugins).

**Docusaurus** supports remote content via plugins.

---

## Goals & Non-Goals

### Goals

1. **G1**: Define abstract `ContentSource` interface for all content origins
2. **G2**: Provide built-in loaders for common sources (Local, GitHub, REST)
3. **G3**: Enable mixing local and remote content seamlessly
4. **G4**: Cache remote content intelligently (ETags, timestamps, hashes)
5. **G5**: Integrate with Content Collections for typed remote content
6. **G6**: Support incremental fetching where possible

### Non-Goals

- **NG1**: Real-time content (SSG is build-time only)
- **NG2**: Write-back to remote sources
- **NG3**: Authentication UI (credentials via env vars/config)
- **NG4**: Full CMS feature parity (just content fetching)
- **NG5**: Replacing specialized tools (use Contentful SDK for Contentful features)

---

## Design Principle: Zero-Cost Unless Used

**This feature is opt-in with zero overhead for users who don't need it.**

### Default Behavior (No Change)

```python
# collections.py - Local-only (current behavior, zero overhead)
collections = {
    "docs": define_collection(schema=Doc, directory="content/docs"),
    "blog": define_collection(schema=BlogPost, directory="content/blog"),
}
# ☝️ No remote loaders = no network calls, no new dependencies
```

### Opt-In Remote Content

```python
# collections.py - With remote sources (opt-in)
collections = {
    "docs": define_collection(schema=Doc, directory="content/docs"),
    "blog": define_collection(
        schema=BlogPost,
        loader=notion_loader(database_id="..."),  # ← Only now does Notion code load
    ),
}
```

### Implementation Strategy

**1. Remote loaders as optional package extras:**

```toml
# pyproject.toml
[project.optional-dependencies]
notion = ["notion-client>=2.0"]
github = ["pygithub>=2.0", "aiohttp>=3.0"]
contentful = ["contentful>=2.0"]
all-sources = ["bengal[notion,github,contentful]"]

# Users install only what they need:
pip install bengal              # Local-only (default)
pip install bengal[github]      # + GitHub source
pip install bengal[notion]      # + Notion source
```

**2. Lazy imports (no load until used):**

```python
# bengal/content_layer/sources/notion.py
def notion_loader(database_id: str):
    """Create Notion content loader."""
    try:
        from notion_client import Client
    except ImportError:
        raise ImportError(
            "notion_loader requires the notion-client package.\n"
            "Install with: pip install bengal[notion]"
        )
    return NotionSource(database_id)
```

**3. No network calls unless explicitly configured:**

| Scenario | Network Calls | Extra Dependencies |
|----------|--------------|-------------------|
| No `collections.py` | ❌ None | ❌ None |
| Local-only collections | ❌ None | ❌ None |
| Remote loader defined but not installed | Clear error | ❌ None |
| Remote loader installed and configured | ✅ At build time | Only what's used |

**4. Build flag for CI safety:**

```toml
# bengal.toml
[build]
remote_content = false  # Disable all remote fetching (CI safety, offline builds)
```

```bash
# Or via CLI
bengal build --offline  # Use cached remote content only
```

---

## Prior Art: Hugo Content Adapters

This design is similar to **Hugo's Content Adapters** (v0.126.0, May 2024), which also fetch content from external sources at build time.

**Hugo approach** (Go templates):
```go
{{/* content/books/_content.gotmpl */}}
{{ $data := dict }}
{{ with resources.GetRemote "https://api.example.com/books.json" }}
  {{ $data = .Content | transform.Unmarshal }}
{{ end }}
{{ range $data.books }}
  {{ $.AddPage (dict "path" .id "title" .title "content" .summary) }}
{{ end }}
```

**Bengal approach** (Python):
```python
# collections.py
collections = {
    "books": define_collection(
        schema=Book,
        loader=rest_loader(url="https://api.example.com/books.json"),
    ),
}
```

**Key differences from Hugo:**

| Aspect | Hugo | Bengal |
|--------|------|--------|
| Language | Go templates | Python |
| Type safety | None | Dataclass/Pydantic validation |
| IDE support | Limited | Full autocomplete |
| Custom loaders | Write Go templates | Write Python classes |
| Error messages | Go template errors | Python exceptions with context |

---

## Architecture Impact

**Affected Subsystems**:

- **Core** (`bengal/core/`): Minor impact
  - Page.source_type: Track content origin

- **Discovery** (`bengal/discovery/`): Major refactor
  - New `content_layer.py` module
  - `ContentSource` abstract base class
  - Source registry and configuration

- **Cache** (`bengal/cache/`): Moderate impact
  - `remote_content_cache.py` - Cache fetched content
  - HTTP caching (ETags, Last-Modified)

- **Config** (`bengal/config/`): Moderate impact
  - Parse `sources` configuration
  - Credential management

- **CLI** (`bengal/cli/`): Minor impact
  - `bengal sources list` - List configured sources
  - `bengal sources fetch` - Pre-fetch remote content
  - `bengal sources clear-cache` - Clear remote cache

**Integration Points**:
- Sources defined in `collections.py` or `bengal.toml`
- All sources return `ContentEntry` objects
- `ContentEntry` → `Page` transformation in discovery

---

## Design Options

### Option A: Abstract Source Interface (Recommended)

**Description**: Define abstract `ContentSource` protocol with async fetching.

```python
# bengal/content_layer/source.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Protocol

@dataclass
class ContentEntry:
    """Unified content entry from any source."""
    id: str                          # Unique identifier
    content: str                     # Raw content (markdown)
    frontmatter: dict[str, Any]      # Metadata
    source_type: str                 # 'local', 'github', 'notion', etc.
    source_url: str | None           # Original URL if applicable
    last_modified: datetime | None   # For cache invalidation
    checksum: str | None             # Content hash

class ContentSource(Protocol):
    """Protocol for content sources."""

    @property
    def source_type(self) -> str:
        """Unique identifier for this source type."""
        ...

    async def fetch(self) -> AsyncIterator[ContentEntry]:
        """Fetch all content from this source."""
        ...

    async def fetch_one(self, id: str) -> ContentEntry | None:
        """Fetch single content entry by ID."""
        ...

    def get_cache_key(self) -> str:
        """Return cache key for this source configuration."""
        ...
```

**Pros**:
- Clean abstraction
- Easy to add new sources
- Testable (mock sources)
- Async-first for performance

**Cons**:
- Requires async infrastructure
- More complex than sync approach

**Complexity**: Medium

---

### Option B: Plugin-Based Sources

**Description**: Sources as installable plugins.

```python
# bengal-source-github (separate package)
from bengal.content_layer import register_source

@register_source("github")
class GitHubSource:
    ...
```

**Pros**:
- Keeps core small
- Community can add sources
- Independent versioning

**Cons**:
- Fragmented ecosystem
- Dependency management complexity
- Discovery problem

**Complexity**: High

---

### Option C: Configuration-Driven Sources

**Description**: Define sources entirely in config.

```toml
# bengal.toml
[[sources]]
type = "github"
repo = "org/docs"
branch = "main"
path = "content/"

[[sources]]
type = "rest"
url = "https://api.example.com/docs"
headers = { Authorization = "${DOCS_API_KEY}" }
```

**Pros**:
- No Python needed
- Easy to understand
- Declarative

**Cons**:
- Limited flexibility
- Can't customize behavior
- Hard to handle edge cases

**Complexity**: Low

---

### Recommended: Option A + C (Protocol with Config)

Combine abstract protocol with configuration-driven setup:

1. **Protocol defines interface** (Option A)
2. **Built-in sources configured via config** (Option C)
3. **Custom sources via Python** (advanced users)

---

## Detailed Design

### 1. Content Entry Model

```python
# bengal/content_layer/entry.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ContentEntry:
    """
    Unified representation of content from any source.

    This is the output of all ContentSource implementations and serves as
    the input to the Page creation process.
    """

    # Identity
    id: str                              # Unique within source (e.g., path, doc ID)
    slug: str                            # URL slug

    # Content
    content: str                         # Raw markdown/content
    frontmatter: dict[str, Any]          # Parsed frontmatter

    # Source metadata
    source_type: str                     # 'local', 'github', 'notion', etc.
    source_name: str                     # Configured source name
    source_url: str | None = None        # Original URL (for attribution)

    # Versioning (for cache invalidation)
    last_modified: datetime | None = None
    checksum: str | None = None          # Content hash
    etag: str | None = None              # HTTP ETag

    # Local cache info
    cached_path: Path | None = None      # Local cache location
    cached_at: datetime | None = None    # When cached

    def to_page_kwargs(self) -> dict[str, Any]:
        """Convert to kwargs for Page creation."""
        return {
            "content": self.content,
            "frontmatter": self.frontmatter,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "slug": self.slug,
        }
```

### 2. Content Source Protocol

```python
# bengal/content_layer/source.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Iterator
import hashlib


class ContentSource(ABC):
    """
    Abstract base class for content sources.

    Implementations fetch content from various origins (local files,
    remote APIs, databases) and return unified ContentEntry objects.
    """

    def __init__(self, name: str, config: dict):
        """
        Initialize source.

        Args:
            name: Unique name for this source instance
            config: Source-specific configuration
        """
        self.name = name
        self.config = config

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return source type identifier (e.g., 'github', 'local')."""
        ...

    @abstractmethod
    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        """
        Fetch all content entries from this source.

        Yields:
            ContentEntry for each piece of content
        """
        ...

    @abstractmethod
    async def fetch_one(self, id: str) -> ContentEntry | None:
        """
        Fetch a single content entry by ID.

        Args:
            id: Source-specific identifier

        Returns:
            ContentEntry if found, None otherwise
        """
        ...

    def get_cache_key(self) -> str:
        """
        Generate cache key for this source configuration.

        Used to invalidate cache when config changes.
        """
        config_str = str(sorted(self.config.items()))
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    async def get_last_modified(self) -> datetime | None:
        """
        Get last modification time for cache invalidation.

        Returns None if unknown or not supported.
        """
        return None

    # Sync convenience methods (wrap async)
    def fetch_all_sync(self) -> Iterator[ContentEntry]:
        """Synchronous wrapper for fetch_all."""
        import asyncio

        async def collect():
            return [entry async for entry in self.fetch_all()]

        entries = asyncio.run(collect())
        yield from entries
```

### 3. Built-in Sources

#### Local Source

```python
# bengal/content_layer/sources/local.py
from pathlib import Path
from datetime import datetime
import hashlib


class LocalSource(ContentSource):
    """
    Content source for local filesystem.

    This is the default source, reading markdown files from a directory.
    """

    source_type = "local"

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.directory = Path(config["directory"])
        self.glob = config.get("glob", "**/*.md")
        self.exclude = config.get("exclude", [])

    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        for path in self.directory.glob(self.glob):
            if self._should_exclude(path):
                continue

            entry = await self._load_file(path)
            if entry:
                yield entry

    async def fetch_one(self, id: str) -> ContentEntry | None:
        path = self.directory / id
        if path.exists():
            return await self._load_file(path)
        return None

    async def _load_file(self, path: Path) -> ContentEntry:
        content = path.read_text()
        frontmatter, body = parse_frontmatter(content)

        stat = path.stat()
        checksum = hashlib.sha256(content.encode()).hexdigest()[:16]

        return ContentEntry(
            id=str(path.relative_to(self.directory)),
            slug=self._path_to_slug(path),
            content=body,
            frontmatter=frontmatter,
            source_type=self.source_type,
            source_name=self.name,
            source_url=None,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            checksum=checksum,
            cached_path=path,
        )

    def _should_exclude(self, path: Path) -> bool:
        rel_path = str(path.relative_to(self.directory))
        return any(fnmatch.fnmatch(rel_path, pattern) for pattern in self.exclude)

    def _path_to_slug(self, path: Path) -> str:
        rel = path.relative_to(self.directory)
        return str(rel.with_suffix("")).replace("\\", "/")
```

#### GitHub Source

```python
# bengal/content_layer/sources/github.py
import aiohttp
from base64 import b64decode
from datetime import datetime


class GitHubSource(ContentSource):
    """
    Content source for GitHub repositories.

    Fetches markdown files from a GitHub repo, supporting both
    public repos and private repos with token authentication.

    Configuration:
        repo: str - Repository in "owner/repo" format
        branch: str - Branch name (default: "main")
        path: str - Directory path within repo (default: "")
        token: str - GitHub token (optional, for private repos)
    """

    source_type = "github"

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.repo = config["repo"]
        self.branch = config.get("branch", "main")
        self.path = config.get("path", "").strip("/")
        self.token = config.get("token") or os.environ.get("GITHUB_TOKEN")
        self.glob = config.get("glob", "**/*.md")

        self.api_base = "https://api.github.com"
        self._headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Bengal-SSG",
        }
        if self.token:
            self._headers["Authorization"] = f"token {self.token}"

    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        async with aiohttp.ClientSession(headers=self._headers) as session:
            # Get tree recursively
            tree_url = f"{self.api_base}/repos/{self.repo}/git/trees/{self.branch}?recursive=1"
            async with session.get(tree_url) as resp:
                resp.raise_for_status()
                data = await resp.json()

            # Filter to markdown files in path
            for item in data.get("tree", []):
                if item["type"] != "blob":
                    continue

                file_path = item["path"]
                if self.path and not file_path.startswith(self.path + "/"):
                    continue

                if not file_path.endswith(".md"):
                    continue

                # Fetch file content
                entry = await self._fetch_file(session, file_path, item["sha"])
                if entry:
                    yield entry

    async def fetch_one(self, id: str) -> ContentEntry | None:
        async with aiohttp.ClientSession(headers=self._headers) as session:
            file_path = f"{self.path}/{id}" if self.path else id
            return await self._fetch_file(session, file_path, sha=None)

    async def _fetch_file(
        self, session: aiohttp.ClientSession, path: str, sha: str | None
    ) -> ContentEntry | None:
        # Get file content
        url = f"{self.api_base}/repos/{self.repo}/contents/{path}?ref={self.branch}"
        async with session.get(url) as resp:
            if resp.status == 404:
                return None
            resp.raise_for_status()
            data = await resp.json()

        # Decode content
        content = b64decode(data["content"]).decode("utf-8")
        frontmatter, body = parse_frontmatter(content)

        # Relative path from configured path
        rel_path = path[len(self.path):].lstrip("/") if self.path else path

        return ContentEntry(
            id=rel_path,
            slug=rel_path.replace(".md", ""),
            content=body,
            frontmatter=frontmatter,
            source_type=self.source_type,
            source_name=self.name,
            source_url=f"https://github.com/{self.repo}/blob/{self.branch}/{path}",
            checksum=sha or data.get("sha"),
            last_modified=None,  # GitHub API doesn't return this directly
        )

    async def get_last_modified(self) -> datetime | None:
        """Get latest commit time for the path."""
        async with aiohttp.ClientSession(headers=self._headers) as session:
            url = f"{self.api_base}/repos/{self.repo}/commits"
            params = {"sha": self.branch, "path": self.path, "per_page": 1}
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if data:
                    date_str = data[0]["commit"]["committer"]["date"]
                    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return None
```

#### REST API Source

```python
# bengal/content_layer/sources/rest.py
import aiohttp
from typing import Any


class RESTSource(ContentSource):
    """
    Content source for REST APIs.

    Fetches content from any REST API that returns JSON with
    configurable field mappings.

    Configuration:
        url: str - API endpoint URL
        headers: dict - Request headers
        content_field: str - JSON path to content (default: "content")
        frontmatter_fields: dict - Mapping of frontmatter to JSON paths
        pagination: dict - Pagination config (optional)
    """

    source_type = "rest"

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.url = config["url"]
        self.headers = config.get("headers", {})
        self.content_field = config.get("content_field", "content")
        self.id_field = config.get("id_field", "id")
        self.frontmatter_mapping = config.get("frontmatter_fields", {})
        self.pagination = config.get("pagination")

        # Expand env vars in headers
        self.headers = {
            k: os.path.expandvars(v) for k, v in self.headers.items()
        }

    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            url = self.url

            while url:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

                # Handle array or object response
                items = data if isinstance(data, list) else data.get("items", data.get("data", [data]))

                for item in items:
                    entry = self._item_to_entry(item)
                    if entry:
                        yield entry

                # Handle pagination
                url = self._get_next_url(data, resp)

    async def fetch_one(self, id: str) -> ContentEntry | None:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            url = f"{self.url.rstrip('/')}/{id}"
            async with session.get(url) as resp:
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                data = await resp.json()
                return self._item_to_entry(data)

    def _item_to_entry(self, item: dict) -> ContentEntry | None:
        # Extract content
        content = self._get_nested(item, self.content_field)
        if not content:
            return None

        # Extract frontmatter
        frontmatter = {}
        for fm_key, json_path in self.frontmatter_mapping.items():
            value = self._get_nested(item, json_path)
            if value is not None:
                frontmatter[fm_key] = value

        item_id = str(self._get_nested(item, self.id_field))

        return ContentEntry(
            id=item_id,
            slug=frontmatter.get("slug", item_id),
            content=content,
            frontmatter=frontmatter,
            source_type=self.source_type,
            source_name=self.name,
            source_url=item.get("url") or item.get("html_url"),
            checksum=None,
        )

    def _get_nested(self, obj: dict, path: str) -> Any:
        """Get nested value by dot-separated path."""
        for key in path.split("."):
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                return None
        return obj

    def _get_next_url(self, data: dict, response: aiohttp.ClientResponse) -> str | None:
        """Extract next page URL from response."""
        if not self.pagination:
            return None

        strategy = self.pagination.get("strategy", "link_header")

        if strategy == "link_header":
            link = response.headers.get("Link", "")
            for part in link.split(","):
                if 'rel="next"' in part:
                    return part.split(";")[0].strip("<> ")

        elif strategy == "cursor":
            cursor_field = self.pagination.get("cursor_field", "next_cursor")
            cursor = self._get_nested(data, cursor_field)
            if cursor:
                return f"{self.url}?cursor={cursor}"

        return None
```

#### Notion Source

```python
# bengal/content_layer/sources/notion.py
import aiohttp
from datetime import datetime


class NotionSource(ContentSource):
    """
    Content source for Notion databases.

    Fetches pages from a Notion database and converts them to markdown.

    Configuration:
        database_id: str - Notion database ID
        token: str - Notion integration token (or NOTION_TOKEN env var)
        property_mapping: dict - Map Notion properties to frontmatter
    """

    source_type = "notion"

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.database_id = config["database_id"]
        self.token = config.get("token") or os.environ.get("NOTION_TOKEN")
        self.property_mapping = config.get("property_mapping", {
            "title": "Name",
            "date": "Date",
            "tags": "Tags",
        })

        if not self.token:
            raise ValueError("Notion token required (config or NOTION_TOKEN env var)")

        self.api_base = "https://api.notion.com/v1"
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        async with aiohttp.ClientSession(headers=self._headers) as session:
            url = f"{self.api_base}/databases/{self.database_id}/query"
            has_more = True
            start_cursor = None

            while has_more:
                body = {}
                if start_cursor:
                    body["start_cursor"] = start_cursor

                async with session.post(url, json=body) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

                for page in data.get("results", []):
                    entry = await self._page_to_entry(session, page)
                    if entry:
                        yield entry

                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")

    async def fetch_one(self, id: str) -> ContentEntry | None:
        async with aiohttp.ClientSession(headers=self._headers) as session:
            url = f"{self.api_base}/pages/{id}"
            async with session.get(url) as resp:
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                page = await resp.json()
                return await self._page_to_entry(session, page)

    async def _page_to_entry(
        self, session: aiohttp.ClientSession, page: dict
    ) -> ContentEntry | None:
        page_id = page["id"]

        # Get page blocks (content)
        content = await self._get_page_content(session, page_id)

        # Extract properties as frontmatter
        frontmatter = self._extract_properties(page)

        # Get slug from title or ID
        slug = frontmatter.get("title", "").lower().replace(" ", "-") or page_id

        return ContentEntry(
            id=page_id,
            slug=slug,
            content=content,
            frontmatter=frontmatter,
            source_type=self.source_type,
            source_name=self.name,
            source_url=page.get("url"),
            last_modified=datetime.fromisoformat(
                page["last_edited_time"].replace("Z", "+00:00")
            ),
        )

    async def _get_page_content(self, session: aiohttp.ClientSession, page_id: str) -> str:
        """Fetch and convert page blocks to markdown."""
        url = f"{self.api_base}/blocks/{page_id}/children"
        blocks = []

        async with session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
            blocks = data.get("results", [])

        return self._blocks_to_markdown(blocks)

    def _blocks_to_markdown(self, blocks: list[dict]) -> str:
        """Convert Notion blocks to markdown."""
        lines = []

        for block in blocks:
            block_type = block.get("type")

            if block_type == "paragraph":
                text = self._rich_text_to_md(block["paragraph"]["rich_text"])
                lines.append(text)

            elif block_type == "heading_1":
                text = self._rich_text_to_md(block["heading_1"]["rich_text"])
                lines.append(f"# {text}")

            elif block_type == "heading_2":
                text = self._rich_text_to_md(block["heading_2"]["rich_text"])
                lines.append(f"## {text}")

            elif block_type == "heading_3":
                text = self._rich_text_to_md(block["heading_3"]["rich_text"])
                lines.append(f"### {text}")

            elif block_type == "bulleted_list_item":
                text = self._rich_text_to_md(block["bulleted_list_item"]["rich_text"])
                lines.append(f"- {text}")

            elif block_type == "numbered_list_item":
                text = self._rich_text_to_md(block["numbered_list_item"]["rich_text"])
                lines.append(f"1. {text}")

            elif block_type == "code":
                code = self._rich_text_to_md(block["code"]["rich_text"])
                lang = block["code"].get("language", "")
                lines.append(f"```{lang}\n{code}\n```")

            elif block_type == "quote":
                text = self._rich_text_to_md(block["quote"]["rich_text"])
                lines.append(f"> {text}")

            elif block_type == "divider":
                lines.append("---")

            lines.append("")  # Blank line between blocks

        return "\n".join(lines)

    def _rich_text_to_md(self, rich_text: list[dict]) -> str:
        """Convert Notion rich text to markdown."""
        parts = []
        for item in rich_text:
            text = item.get("plain_text", "")
            annotations = item.get("annotations", {})

            if annotations.get("bold"):
                text = f"**{text}**"
            if annotations.get("italic"):
                text = f"*{text}*"
            if annotations.get("code"):
                text = f"`{text}`"
            if annotations.get("strikethrough"):
                text = f"~~{text}~~"

            # Handle links
            if item.get("href"):
                text = f"[{text}]({item['href']})"

            parts.append(text)

        return "".join(parts)

    def _extract_properties(self, page: dict) -> dict:
        """Extract Notion properties as frontmatter."""
        frontmatter = {}
        properties = page.get("properties", {})

        for fm_key, notion_prop in self.property_mapping.items():
            if notion_prop not in properties:
                continue

            prop = properties[notion_prop]
            prop_type = prop.get("type")

            if prop_type == "title":
                frontmatter[fm_key] = self._rich_text_to_md(prop["title"])
            elif prop_type == "rich_text":
                frontmatter[fm_key] = self._rich_text_to_md(prop["rich_text"])
            elif prop_type == "date":
                if prop["date"]:
                    frontmatter[fm_key] = prop["date"]["start"]
            elif prop_type == "multi_select":
                frontmatter[fm_key] = [opt["name"] for opt in prop["multi_select"]]
            elif prop_type == "select":
                if prop["select"]:
                    frontmatter[fm_key] = prop["select"]["name"]
            elif prop_type == "checkbox":
                frontmatter[fm_key] = prop["checkbox"]
            elif prop_type == "number":
                frontmatter[fm_key] = prop["number"]
            elif prop_type == "url":
                frontmatter[fm_key] = prop["url"]

        return frontmatter
```

### 4. Content Layer Manager

```python
# bengal/content_layer/manager.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator
import json
import logging

from .entry import ContentEntry
from .source import ContentSource
from .sources.local import LocalSource
from .sources.github import GitHubSource
from .sources.rest import RESTSource
from .sources.notion import NotionSource

logger = logging.getLogger(__name__)


# Source type registry
SOURCE_TYPES: dict[str, type[ContentSource]] = {
    "local": LocalSource,
    "github": GitHubSource,
    "rest": RESTSource,
    "notion": NotionSource,
}


@dataclass
class CacheEntry:
    """Cached content entry with metadata."""
    entry: ContentEntry
    cached_at: datetime
    source_key: str


class ContentLayerManager:
    """
    Manages content from multiple sources.

    Handles source registration, fetching, caching, and aggregation.
    """

    def __init__(
        self,
        cache_dir: Path,
        cache_ttl: timedelta = timedelta(hours=1),
    ):
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        self.sources: dict[str, ContentSource] = {}
        self._cache: dict[str, CacheEntry] = {}

        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def register_source(self, name: str, source_type: str, config: dict) -> None:
        """
        Register a content source.

        Args:
            name: Unique name for this source
            source_type: Type identifier (local, github, rest, notion)
            config: Source-specific configuration
        """
        if source_type not in SOURCE_TYPES:
            raise ValueError(f"Unknown source type: {source_type}")

        source_class = SOURCE_TYPES[source_type]
        self.sources[name] = source_class(name, config)
        logger.info(f"Registered source: {name} ({source_type})")

    def register_custom_source(self, name: str, source: ContentSource) -> None:
        """Register a custom source instance."""
        self.sources[name] = source

    async def fetch_all(self, use_cache: bool = True) -> list[ContentEntry]:
        """
        Fetch content from all sources.

        Args:
            use_cache: Whether to use cached content if available

        Returns:
            List of all content entries from all sources
        """
        entries = []

        # Fetch from all sources concurrently
        tasks = [
            self._fetch_source(name, source, use_cache)
            for name, source in self.sources.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for name, result in zip(self.sources.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch from {name}: {result}")
            else:
                entries.extend(result)

        return entries

    async def _fetch_source(
        self, name: str, source: ContentSource, use_cache: bool
    ) -> list[ContentEntry]:
        """Fetch content from a single source with caching."""
        cache_key = f"{name}:{source.get_cache_key()}"
        cache_file = self.cache_dir / f"{name}.json"

        # Check cache
        if use_cache and cache_file.exists():
            cached = self._load_cache(cache_file)
            if cached and self._is_cache_valid(cached, source):
                logger.debug(f"Using cached content for {name}")
                return [e.entry for e in cached]

        # Fetch fresh content
        logger.info(f"Fetching content from {name}...")
        entries = []
        async for entry in source.fetch_all():
            entries.append(entry)

        # Save to cache
        self._save_cache(cache_file, entries, cache_key)
        logger.info(f"Fetched {len(entries)} entries from {name}")

        return entries

    def _is_cache_valid(self, cached: list[CacheEntry], source: ContentSource) -> bool:
        """Check if cached content is still valid."""
        if not cached:
            return False

        # Check TTL
        oldest = min(e.cached_at for e in cached)
        if datetime.now() - oldest > self.cache_ttl:
            return False

        # Check if source config changed
        expected_key = f"{source.name}:{source.get_cache_key()}"
        if any(e.source_key != expected_key for e in cached):
            return False

        return True

    def _load_cache(self, path: Path) -> list[CacheEntry] | None:
        """Load cached entries from disk."""
        try:
            data = json.loads(path.read_text())
            return [
                CacheEntry(
                    entry=ContentEntry(**e["entry"]),
                    cached_at=datetime.fromisoformat(e["cached_at"]),
                    source_key=e["source_key"],
                )
                for e in data
            ]
        except Exception as e:
            logger.debug(f"Failed to load cache: {e}")
            return None

    def _save_cache(self, path: Path, entries: list[ContentEntry], source_key: str) -> None:
        """Save entries to cache."""
        now = datetime.now()
        data = [
            {
                "entry": {
                    "id": e.id,
                    "slug": e.slug,
                    "content": e.content,
                    "frontmatter": e.frontmatter,
                    "source_type": e.source_type,
                    "source_name": e.source_name,
                    "source_url": e.source_url,
                    "last_modified": e.last_modified.isoformat() if e.last_modified else None,
                    "checksum": e.checksum,
                },
                "cached_at": now.isoformat(),
                "source_key": source_key,
            }
            for e in entries
        ]
        path.write_text(json.dumps(data, indent=2))

    def clear_cache(self, source_name: str | None = None) -> None:
        """Clear cached content."""
        if source_name:
            cache_file = self.cache_dir / f"{source_name}.json"
            if cache_file.exists():
                cache_file.unlink()
        else:
            for f in self.cache_dir.glob("*.json"):
                f.unlink()

    # Sync convenience methods
    def fetch_all_sync(self, use_cache: bool = True) -> list[ContentEntry]:
        """Synchronous wrapper for fetch_all."""
        return asyncio.run(self.fetch_all(use_cache))
```

### 5. Configuration Integration

```toml
# bengal.toml

# Define content sources
[[sources]]
name = "local-docs"
type = "local"
directory = "content/docs"

[[sources]]
name = "api-docs"
type = "github"
repo = "myorg/api-docs"
branch = "main"
path = "docs"
# token from GITHUB_TOKEN env var

[[sources]]
name = "blog"
type = "notion"
database_id = "abc123..."
# token from NOTION_TOKEN env var
[sources.property_mapping]
title = "Name"
date = "Published"
tags = "Tags"
author = "Author"

[[sources]]
name = "external-api"
type = "rest"
url = "https://api.example.com/docs"
content_field = "body"
id_field = "slug"
[sources.headers]
Authorization = "Bearer ${DOCS_API_KEY}"
[sources.frontmatter_fields]
title = "title"
date = "published_at"
```

### Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Source Configuration                               │
│                                                                          │
│  bengal.toml:                                                            │
│    [[sources]]                                                           │
│    name = "docs"         [[sources]]          [[sources]]                │
│    type = "local"        name = "api"         name = "blog"              │
│    directory = "..."     type = "github"      type = "notion"            │
└─────────────┬─────────────────┬─────────────────────┬────────────────────┘
              │                 │                     │
              ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ContentLayerManager                                  │
│                                                                          │
│  1. Register sources from config                                         │
│  2. Check cache validity (TTL, config hash)                              │
│  3. Fetch from sources (parallel async)                                  │
│  4. Cache results to disk                                                │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        ContentEntry[]                                    │
│                                                                          │
│  Unified representation regardless of source:                            │
│  - id, slug                                                              │
│  - content (markdown)                                                    │
│  - frontmatter (dict)                                                    │
│  - source_type, source_url                                               │
│  - last_modified, checksum                                               │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Collection Validation                                 │
│                                                                          │
│  (If collections defined - see RFC-Content-Collections)                  │
│  Validate frontmatter against typed schemas                              │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Page Creation                                     │
│                                                                          │
│  ContentEntry → Page (existing Bengal page model)                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

- [ ] Create `bengal/content_layer/` package structure
- [ ] Implement `ContentEntry` dataclass
- [ ] Implement `ContentSource` abstract base class
- [ ] Implement `LocalSource` (migrate existing discovery)
- [ ] Implement `ContentLayerManager`
- [ ] Unit tests for core components

### Phase 2: Remote Sources (Week 2)

- [ ] Implement `GitHubSource`
- [ ] Implement `RESTSource`
- [ ] Implement `NotionSource`
- [ ] Add async HTTP client (aiohttp)
- [ ] Integration tests with mock servers

### Phase 3: Caching (Week 2)

- [ ] Implement disk caching in `ContentLayerManager`
- [ ] Add cache invalidation logic (TTL, checksums, config hash)
- [ ] Add HTTP caching (ETags, Last-Modified)
- [ ] Benchmark cache performance

### Phase 4: Configuration & CLI (Week 3)

- [ ] Add `[[sources]]` config parsing
- [ ] Add `bengal sources list` command
- [ ] Add `bengal sources fetch` command
- [ ] Add `bengal sources clear-cache` command
- [ ] Environment variable expansion in config

### Phase 5: Integration (Week 3)

- [ ] Integrate with existing discovery pipeline
- [ ] Integrate with Content Collections (validation)
- [ ] Update `Site` to use `ContentLayerManager`
- [ ] End-to-end tests

### Phase 6: Documentation (Week 4)

- [ ] Document source configuration
- [ ] Document each built-in source
- [ ] Add examples for common patterns
- [ ] Document custom source creation

---

## Tradeoffs & Risks

### Tradeoffs

| Gain | Lose |
|------|------|
| Unified content from anywhere | Build depends on external services |
| CMS integration | Network latency during builds |
| Multi-repo aggregation | Credential management complexity |
| Remote content caching | Cache invalidation challenges |

### Risks

#### Risk 1: Build Reliability

**Description**: Builds fail when remote sources unavailable

- **Likelihood**: Medium
- **Impact**: High
- **Mitigation**:
  - Aggressive caching (use stale if fetch fails)
  - `--offline` flag to use cached content only
  - Health checks before build starts
  - Clear error messages with source attribution

#### Risk 2: Rate Limiting

**Description**: GitHub/Notion APIs have rate limits

- **Likelihood**: High (for large sites)
- **Impact**: Medium
- **Mitigation**:
  - Implement exponential backoff
  - Cache aggressively
  - Support authenticated requests (higher limits)
  - Pre-fetch in CI with caching

#### Risk 3: Content Consistency

**Description**: Remote content changes during build

- **Likelihood**: Low
- **Impact**: Low
- **Mitigation**:
  - Fetch all content before rendering starts
  - Lock content versions (Git SHA, timestamps)
  - Warn if content changes mid-build

#### Risk 4: Security (Credentials)

**Description**: Tokens exposed in config or logs

- **Likelihood**: Medium
- **Impact**: High
- **Mitigation**:
  - Environment variables only (no tokens in config files)
  - Mask tokens in logs
  - Document secure credential management
  - Support secret managers

---

## Future Considerations

1. **GraphQL Source**: For headless CMS with GraphQL APIs
2. **Contentful/Sanity/Strapi**: First-class CMS integrations
3. **Database Source**: Direct database queries (SQLite, PostgreSQL)
4. **Git Sync**: Two-way sync for editing remote content locally
5. **Webhooks**: Trigger rebuilds on content changes
6. **Content Versioning**: Support multiple content versions

---

## Related Work

- [Astro Content Layer](https://astro.build/blog/astro-4140/)
- [Gatsby Source Plugins](https://www.gatsbyjs.com/docs/how-to/plugins-and-themes/creating-a-source-plugin/)
- [Docusaurus Remote Content](https://docusaurus.io/docs/api/plugins/@docusaurus/plugin-content-docs)
- [RFC-Content-Collections](rfc-content-collections.md) (dependency)

---

## Approval

- [ ] RFC reviewed
- [ ] Source interface approved
- [ ] Built-in sources approved
- [ ] Implementation plan approved

---

## RFC Quality Checklist

- [x] Problem statement clear with evidence
- [x] Goals and non-goals explicit
- [x] At least 2 design options analyzed (3 provided)
- [x] Recommended option justified
- [x] Architecture impact documented
- [x] Risks identified with mitigations
- [x] Implementation phases defined (4 weeks)
- [x] Configuration example provided
- [x] Confidence ≥ 85% (88%)
