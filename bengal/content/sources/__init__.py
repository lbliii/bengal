"""
Content Layer - Unified content abstraction for Bengal.

This module provides a content layer API that fetches content from any source:
local files, GitHub repos, REST APIs, Notion databases, and more.

Design Principle: ZERO-COST UNLESS USED
=======================================
- Local-only collections have zero overhead
- Remote loaders only activate when configured
- CMS SDKs are lazy-loaded (import only when their loader is used)
- No network calls unless explicitly configured

Usage (Local Only - Default):

```python
# collections.py
from bengal.collections import define_collection

collections = {
    "docs": define_collection(schema=Doc, directory="content/docs"),
}
# ☝️ No remote loaders = no network calls, no new dependencies
```

Usage (With Remote Sources - Opt-in):

```python
from bengal.collections import define_collection
from bengal.content.sources import github_loader, notion_loader

collections = {
    "docs": define_collection(schema=Doc, directory="content/docs"),
    "blog": define_collection(
        schema=BlogPost,
        loader=notion_loader(database_id="abc123"),
    ),
    "api-docs": define_collection(
        schema=APIDoc,
        loader=github_loader(repo="myorg/api-docs", path="docs/"),
    ),
}
```

Installation:
pip install bengal              # Local-only (default)
pip install bengal[github]      # + GitHub source
pip install bengal[notion]      # + Notion source
pip install bengal[all-sources] # All remote sources

Related:
- bengal/collections/: Content collections with schema validation
- bengal/content/discovery/: Content discovery (uses content layer internally)
- plan/active/rfc-content-layer-api.md: Design document

"""

from __future__ import annotations

from bengal.content.sources.entry import ContentEntry

# Loader factory functions (lazy import actual sources)
from bengal.content.sources.loaders import (
    github_loader,
    local_loader,
    notion_loader,
    rest_loader,
)
from bengal.content.sources.manager import ContentLayerManager
from bengal.content.sources.source import ContentSource

# Source registry - maps type names to source classes
# Remote sources use lazy loading to avoid importing heavy dependencies
SOURCE_REGISTRY: dict[str, type[ContentSource]] = {}


def _register_local_source() -> None:
    """Register the local source (always available)."""
    from bengal.content.sources.local import LocalSource

    SOURCE_REGISTRY["local"] = LocalSource
    SOURCE_REGISTRY["filesystem"] = LocalSource  # Alias


def _register_github_source() -> None:
    """Register GitHub source if aiohttp is available."""
    try:
        from bengal.content.sources.github import GitHubSource

        SOURCE_REGISTRY["github"] = GitHubSource
    except ImportError:
        pass  # aiohttp not installed


def _register_rest_source() -> None:
    """Register REST source if aiohttp is available."""
    try:
        from bengal.content.sources.rest import RESTSource

        SOURCE_REGISTRY["rest"] = RESTSource
        SOURCE_REGISTRY["api"] = RESTSource  # Alias
    except ImportError:
        pass  # aiohttp not installed


def _register_notion_source() -> None:
    """Register Notion source if aiohttp is available."""
    try:
        from bengal.content.sources.notion import NotionSource

        SOURCE_REGISTRY["notion"] = NotionSource
    except ImportError:
        pass  # aiohttp not installed


# Register available sources
_register_local_source()
_register_github_source()
_register_rest_source()
_register_notion_source()


def get_available_sources() -> list[str]:
    """Get list of available source types."""
    return sorted(SOURCE_REGISTRY.keys())


def is_source_available(source_type: str) -> bool:
    """Check if a source type is available."""
    return source_type in SOURCE_REGISTRY


__all__ = [
    "SOURCE_REGISTRY",
    # Core types
    "ContentEntry",
    "ContentLayerManager",
    "ContentSource",
    "get_available_sources",
    "github_loader",
    "is_source_available",
    # Loader factories
    "local_loader",
    "notion_loader",
    "rest_loader",
]
