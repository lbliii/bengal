"""
Content loader factory functions.

These are the user-facing functions for creating content sources.
They provide a clean API and handle lazy loading of dependencies.

Usage:

```python
from bengal.content_layer import local_loader, github_loader

collections = {
    "docs": define_collection(schema=Doc, loader=local_loader("content/docs")),
    "api": define_collection(schema=API, loader=github_loader(repo="org/api")),
}
```
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.content_layer.source import ContentSource


def local_loader(
    directory: str | Path,
    *,
    glob: str = "**/*.md",
    exclude: list[str] | None = None,
) -> ContentSource:
    """
    Create a local filesystem content loader.

    Args:
        directory: Path to content directory (relative to site root)
        glob: Glob pattern for matching files (default: all .md files)
        exclude: List of patterns to exclude

    Returns:
        LocalSource instance

    Example:
        >>> from bengal.content_layer import local_loader
        >>> loader = local_loader("content/docs", exclude=["_drafts/*"])
    """
    from bengal.content_layer.sources.local import LocalSource

    config = {
        "directory": str(directory),
        "glob": glob,
        "exclude": exclude or [],
    }
    return LocalSource(name=f"local:{directory}", config=config)


def github_loader(
    repo: str,
    *,
    branch: str = "main",
    path: str = "",
    token: str | None = None,
    glob: str = "*.md",
) -> ContentSource:
    """
    Create a GitHub repository content loader.

    Fetches markdown files from a GitHub repository. Supports both
    public and private repositories (with token).

    Args:
        repo: Repository in "owner/repo" format
        branch: Branch name (default: "main")
        path: Directory path within repo (default: root)
        token: GitHub token (default: uses GITHUB_TOKEN env var)
        glob: File pattern to match (default: "*.md")

    Returns:
        GitHubSource instance

    Requires:
        pip install bengal[github]

    Example:
        >>> from bengal.content_layer import github_loader
        >>> loader = github_loader(
        ...     repo="myorg/docs",
        ...     path="content/api",
        ...     branch="main",
        ... )
    """
    try:
        from bengal.content_layer.sources.github import GitHubSource
    except ImportError as e:
        raise ImportError(
            "github_loader requires aiohttp.\nInstall with: pip install bengal[github]"
        ) from e

    config = {
        "repo": repo,
        "branch": branch,
        "path": path,
        "glob": glob,
    }
    if token:
        config["token"] = token

    return GitHubSource(name=f"github:{repo}", config=config)


def rest_loader(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    content_field: str = "content",
    id_field: str = "id",
    frontmatter_fields: dict[str, str] | None = None,
    items_path: str | None = None,
    pagination: dict[str, Any] | None = None,
) -> ContentSource:
    """
    Create a REST API content loader.

    Fetches content from any REST API that returns JSON.

    Args:
        url: API endpoint URL
        headers: Request headers (supports ${ENV_VAR} expansion)
        content_field: JSON path to content (default: "content")
        id_field: JSON path to ID (default: "id")
        frontmatter_fields: Mapping of frontmatter keys to JSON paths
        items_path: JSON path to items array (default: auto-detect)
        pagination: Pagination config dict with:
            - strategy: "link_header", "cursor", or "offset"
            - cursor_field: Field containing next cursor
            - cursor_param: Query param name for cursor

    Returns:
        RESTSource instance

    Requires:
        pip install bengal[rest]  # includes aiohttp

    Example:
        >>> from bengal.content_layer import rest_loader
        >>> loader = rest_loader(
        ...     url="https://api.example.com/posts",
        ...     headers={"Authorization": "Bearer ${API_TOKEN}"},
        ...     content_field="body",
        ...     frontmatter_fields={
        ...         "title": "title",
        ...         "date": "published_at",
        ...     },
        ... )
    """
    try:
        from bengal.content_layer.sources.rest import RESTSource
    except ImportError as e:
        raise ImportError(
            "rest_loader requires aiohttp.\nInstall with: pip install bengal[rest]"
        ) from e

    config: dict[str, Any] = {
        "url": url,
        "content_field": content_field,
        "id_field": id_field,
    }
    if headers:
        config["headers"] = headers
    if frontmatter_fields:
        config["frontmatter_fields"] = frontmatter_fields
    if items_path:
        config["items_path"] = items_path
    if pagination:
        config["pagination"] = pagination

    return RESTSource(name=f"rest:{url}", config=config)


def notion_loader(
    database_id: str,
    *,
    token: str | None = None,
    property_mapping: dict[str, str] | None = None,
    filter: dict[str, Any] | None = None,
    sorts: list[dict[str, Any]] | None = None,
) -> ContentSource:
    """
    Create a Notion database content loader.

    Fetches pages from a Notion database and converts them to markdown.

    Args:
        database_id: Notion database ID (from URL or API)
        token: Notion integration token (default: uses NOTION_TOKEN env var)
        property_mapping: Map Notion properties to frontmatter fields
            Default: {"title": "Name", "date": "Date", "tags": "Tags"}
        filter: Notion filter object for querying
        sorts: Notion sorts array for ordering

    Returns:
        NotionSource instance

    Requires:
        pip install bengal[notion]

    Setup:
        1. Create integration at https://www.notion.so/my-integrations
        2. Share database with the integration
        3. Set NOTION_TOKEN env var or pass token parameter

    Example:
        >>> from bengal.content_layer import notion_loader
        >>> loader = notion_loader(
        ...     database_id="abc123...",
        ...     property_mapping={
        ...         "title": "Name",
        ...         "date": "Published",
        ...         "tags": "Tags",
        ...         "author": "Author",
        ...     },
        ... )
    """
    try:
        from bengal.content_layer.sources.notion import NotionSource
    except ImportError as e:
        raise ImportError(
            "notion_loader requires aiohttp.\nInstall with: pip install bengal[notion]"
        ) from e

    config: dict[str, Any] = {
        "database_id": database_id,
    }
    if token:
        config["token"] = token
    if property_mapping:
        config["property_mapping"] = property_mapping
    if filter:
        config["filter"] = filter
    if sorts:
        config["sorts"] = sorts

    return NotionSource(name=f"notion:{database_id[:8]}", config=config)


__all__ = [
    "local_loader",
    "github_loader",
    "rest_loader",
    "notion_loader",
]
