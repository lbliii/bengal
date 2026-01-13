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
      avatar: "/images/authors/jane.jpg"
      url: "https://janesmith.dev"
      social:
        twitter: "janesmith"
        github: "janesmith"

Multiple authors:
    authors:
      - "Jane Smith"
      - "Bob Jones"

Multiple authors with details:
    authors:
      - name: "Jane Smith"
        email: "jane@example.com"
        avatar: "/images/authors/jane.jpg"
      - name: "Bob Jones"

Template Usage:
{# Get all posts by an author #}
{% set posts = site.indexes.author.get('Jane Smith') %}

{# List all authors with metadata #}
{% for author in site.indexes.author.keys() %}
  {% set meta = site.indexes.author.get_metadata(author) %}
  <div class="author">
    {% if meta.avatar %}
      <img src="{{ meta.avatar }}" alt="{{ author }}">
    {% endif %}
    <span>{{ author }}</span>
    <small>{{ site.indexes.author.get(author)|length }} posts</small>
  </div>
{% endfor %}

Related:
- bengal.cache.query_index: Base QueryIndex class
- bengal.cache.indexes.category_index: Similar single-valued index
- bengal.core.author: Author dataclass for structured author data

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
          avatar: "/images/authors/jane.jpg"
          social:
            twitter: "janesmith"
            github: "janesmith"
    
    Provides O(1) lookup:
        site.indexes.author.get('Jane Smith')   # All posts by Jane
    
    Multi-author support (multi-valued index):
        authors: ["Jane Smith", "Bob Jones"]    # Both authors get index entry
    
    Rich metadata support:
        site.indexes.author.get_metadata('Jane Smith')
        # Returns: {email: "...", bio: "...", avatar: "...", url: "...", social: {...}}
        
    """

    def __init__(self, cache_path: Path):
        super().__init__("author", cache_path)

    def extract_keys(self, page: Page) -> list[tuple[str, dict[str, Any]]]:
        """Extract author(s) from page metadata with full structured data."""
        keys = []

        # Check for 'author' field (single author)
        author = page.metadata.get("author")
        if author:
            extracted = self._extract_author_data(author)
            if extracted:
                keys.append(extracted)

        # Check for 'authors' field (multiple authors)
        authors = page.metadata.get("authors")
        if authors and isinstance(authors, list):
            for author_item in authors:
                extracted = self._extract_author_data(author_item)
                if extracted:
                    keys.append(extracted)

        return keys

    def _extract_author_data(
        self, author: str | dict[str, Any]
    ) -> tuple[str, dict[str, Any]] | None:
        """
        Extract structured author data from frontmatter value.

        Args:
            author: Author data (string name or dict with details)

        Returns:
            Tuple of (author_name, metadata_dict) or None if invalid
        """
        if isinstance(author, str):
            # Simple string format - just the name
            return (author, {})

        if isinstance(author, dict):
            name = author.get("name")
            if not name:
                return None

            # Extract all supported author metadata
            metadata: dict[str, Any] = {
                "email": author.get("email", ""),
                "bio": author.get("bio", ""),
                "avatar": author.get("avatar", ""),
                "url": author.get("url", ""),
            }

            # Extract social links as nested dict
            social = author.get("social")
            if social and isinstance(social, dict):
                metadata["social"] = {
                    "twitter": social.get("twitter", ""),
                    "github": social.get("github", ""),
                    "linkedin": social.get("linkedin", ""),
                    "mastodon": social.get("mastodon", ""),
                    # Store any additional social links
                    **{
                        k: v
                        for k, v in social.items()
                        if k not in ("twitter", "github", "linkedin", "mastodon")
                    },
                }
            else:
                metadata["social"] = {}

            return (str(name), metadata)

        return None
