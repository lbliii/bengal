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
from bengal.content_layer import github_loader, notion_loader

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
    - bengal/discovery/: Content discovery (uses content layer internally)
    - plan/active/rfc-content-layer-api.md: Design document
"""

from __future__ import annotations

from bengal.content_layer.entry import ContentEntry

# Loader factory functions (lazy import actual sources)
from bengal.content_layer.loaders import (
    github_loader,
    local_loader,
    notion_loader,
    rest_loader,
)
from bengal.content_layer.manager import ContentLayerManager
from bengal.content_layer.source import ContentSource

__all__ = [
    # Core types
    "ContentEntry",
    "ContentSource",
    "ContentLayerManager",
    # Loader factories
    "local_loader",
    "github_loader",
    "rest_loader",
    "notion_loader",
]
