"""
Page-related type definitions for Bengal SSG.

Provides dataclasses and TypedDicts for structured data used across
the page, metadata, and cascade subsystems.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict


@dataclass(frozen=True, slots=True)
class TOCItem:
    """
    Structured table of contents item from markdown headings.

    Used by toc_items property and build_toc_tree for template rendering.
    Flat items (from extract_toc_structure) have empty children;
    nested items (from build_toc_tree) have populated children.
    """

    id: str
    title: str
    level: int
    children: tuple[TOCItem, ...] = ()


@dataclass(frozen=True, slots=True)
class VisibilitySettings:
    """Immutable visibility settings for thread-safe parallel render."""

    menu: bool = True
    listings: bool = True
    sitemap: bool = True
    robots: str = "index, follow"
    render: str = "always"
    search: bool = True
    rss: bool = True
    ai_train: bool = False
    ai_input: bool = True

    def __getitem__(self, key: str) -> bool | str:
        """Allow dict-like access for backward compatibility (e.g. visibility['ai_train'])."""
        return getattr(self, key)

    def get(self, key: str, default: bool | str = True) -> bool | str:
        """Dict-like get for backward compatibility (e.g. visibility.get('menu', True))."""
        return getattr(self, key, default)


class CascadeBlock(TypedDict, total=False):
    """Cascade block from _index.md frontmatter."""

    target: str
    values: dict[str, Any]
