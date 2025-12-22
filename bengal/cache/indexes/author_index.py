"""
Author index for O(1) lookup of pages by author.

This module provides AuthorIndex, a QueryIndex implementation that indexes pages
by their author(s). Supports both single author and multi-author scenarios.

Frontmatter Formats:
    Single author (string):
        author: "Jane Smith"

    Single author (dict with details):
        author:
          name: "Jane Smith"
          email: "jane@example.com"
          bio: "Python enthusiast"

    Multiple authors:
        authors:
          - "Jane Smith"
          - "Bob Jones"

    Multiple authors with details:
        authors:
          - name: "Jane Smith"
            email: "jane@example.com"
          - name: "Bob Jones"

Template Usage:
    {# Get all posts by an author #}
    {% set posts = site.indexes.author.get('Jane Smith') %}

    {# List all authors #}
    {% for author in site.indexes.author.keys() %}
      {{ author }}: {{ site.indexes.author.get(author)|length }} posts
    {% endfor %}

Related:
    - bengal.cache.query_index: Base QueryIndex class
    - bengal.cache.indexes.category_index: Similar single-valued index
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.cache.query_index import QueryIndex

if TYPE_CHECKING:
    from bengal.core.page import Page


class AuthorIndex(QueryIndex):
    """
    Index pages by author.

    Supports both string and dict author formats:
        author: "Jane Smith"

        # Or with details:
        author:
          name: "Jane Smith"
          email: "jane@example.com"
          bio: "Python enthusiast"

    Provides O(1) lookup:
        site.indexes.author.get('Jane Smith')   # All posts by Jane

    Multi-author support (multi-valued index):
        authors: ["Jane Smith", "Bob Jones"]    # Both authors get index entry
    """

    def __init__(self, cache_path: Path):
        super().__init__("author", cache_path)

    def extract_keys(self, page: Page) -> list[tuple[str, dict[str, Any]]]:
        """Extract author(s) from page metadata."""
        keys = []

        # Check for 'author' field (single author)
        author = page.metadata.get("author")
        if author:
            if isinstance(author, dict):
                # Author as dict: {name: "Jane", email: "jane@..."}
                name = author.get("name")
                if name:
                    metadata = {
                        "email": author.get("email", ""),
                        "bio": author.get("bio", ""),
                    }
                    keys.append((name, metadata))
            elif isinstance(author, str):
                # Author as string
                keys.append((author, {}))

        # Check for 'authors' field (multiple authors)
        authors = page.metadata.get("authors")
        if authors and isinstance(authors, list):
            for author_item in authors:
                if isinstance(author_item, dict):
                    name = author_item.get("name")
                    if name:
                        metadata = {
                            "email": author_item.get("email", ""),
                            "bio": author_item.get("bio", ""),
                        }
                        keys.append((name, metadata))
                elif isinstance(author_item, str):
                    keys.append((author_item, {}))

        return keys
