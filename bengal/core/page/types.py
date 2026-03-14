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


class VisibilitySettings(TypedDict, total=False):
    """Granular visibility settings for page inclusion."""

    menu: bool
    listings: bool
    sitemap: bool
    robots: str
    render: str
    search: bool
    rss: bool
    ai_train: bool
    ai_input: bool


class CascadeBlock(TypedDict, total=False):
    """Cascade block from _index.md frontmatter."""

    target: str
    values: dict[str, Any]
