"""
Content acquisition for Bengal.

Combines discovery (finding local content/assets) and sources (loading remote content).
"""

from __future__ import annotations

__all__ = [
    "AssetDiscovery",
    "ContentDiscovery",
    "GitVersionAdapter",
    "VersionResolver",
    "ContentEntry",
    "ContentSource",
    "ContentLayerManager",
    "local_loader",
    "github_loader",
    "rest_loader",
    "notion_loader",
]


def __getattr__(name: str) -> object:
    if name in {"AssetDiscovery", "ContentDiscovery", "GitVersionAdapter", "VersionResolver"}:
        from bengal.content import discovery

        return getattr(discovery, name)
    if name in {
        "ContentEntry",
        "ContentSource",
        "ContentLayerManager",
        "local_loader",
        "github_loader",
        "rest_loader",
        "notion_loader",
    }:
        from bengal.content import sources

        return getattr(sources, name)
    raise AttributeError(f"module 'bengal.content' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted([*globals().keys(), *__all__])
