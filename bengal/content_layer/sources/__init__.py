"""
Content source implementations.

Built-in sources:
- LocalSource: Local filesystem
- GitHubSource: GitHub repositories
- RESTSource: REST APIs
- NotionSource: Notion databases

Remote sources are lazy-loaded to avoid importing dependencies unless needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.content_layer.source import ContentSource

# Source registry - maps type names to source classes
# Remote sources use lazy loading to avoid importing heavy dependencies
SOURCE_REGISTRY: dict[str, type[ContentSource]] = {}


def _register_local_source() -> None:
    """Register the local source (always available)."""
    from bengal.content_layer.sources.local import LocalSource

    SOURCE_REGISTRY["local"] = LocalSource
    SOURCE_REGISTRY["filesystem"] = LocalSource  # Alias


def _register_github_source() -> None:
    """Register GitHub source if aiohttp is available."""
    try:
        from bengal.content_layer.sources.github import GitHubSource

        SOURCE_REGISTRY["github"] = GitHubSource
    except ImportError:
        pass  # aiohttp not installed


def _register_rest_source() -> None:
    """Register REST source if aiohttp is available."""
    try:
        from bengal.content_layer.sources.rest import RESTSource

        SOURCE_REGISTRY["rest"] = RESTSource
        SOURCE_REGISTRY["api"] = RESTSource  # Alias
    except ImportError:
        pass  # aiohttp not installed


def _register_notion_source() -> None:
    """Register Notion source if aiohttp is available."""
    try:
        from bengal.content_layer.sources.notion import NotionSource

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
    "get_available_sources",
    "is_source_available",
]
