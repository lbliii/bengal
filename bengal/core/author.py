"""
Author model for content attribution.

Provides a structured dataclass for representing content authors with support
for rich metadata like social links, avatars, and bios.

Public API:
Author: Content author representation with social links and avatar

Frontmatter Formats:
Single author (string):
    author: "Jane Smith"

Single author (dict with details):
    author:
      name: "Jane Smith"
      email: "jane@example.com"
      bio: "Python enthusiast and tech writer"
      avatar: "/images/authors/jane.jpg"
      social:
        twitter: "janesmith"
        github: "janesmith"

Multiple authors:
    authors:
      - name: "Jane Smith"
        email: "jane@example.com"
      - name: "Bob Jones"
        github: "bobjones"

Template Usage:
{{ page.author.name }}
{{ page.author.avatar }}
{% if page.author.social.twitter %}
  <a href="https://twitter.com/{{ page.author.social.twitter }}">Twitter</a>
{% endif %}

{% for author in page.authors %}
  <span class="author">{{ author.name }}</span>
{% endfor %}

Related Modules:
- bengal.core.page.computed: Page computed properties using Author
- bengal.cache.indexes.author_index: Author-based page index

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Author:
    """
    Content author with structured metadata.

    This dataclass represents a content author with support for:
    - Basic info: name, email, bio
    - Avatar image for visual identification
    - Social links for various platforms

    The class is frozen (immutable) for hashability and cache safety.

    Attributes:
        name: Display name (required)
        email: Contact email (optional)
        bio: Short biography (optional)
        avatar: Path to avatar image (optional)
        social: Dictionary of social platform handles (optional)
        url: Personal website URL (optional)

    Example:
            >>> author = Author(
            ...     name="Jane Smith",
            ...     email="jane@example.com",
            ...     bio="Python enthusiast",
            ...     avatar="/images/authors/jane.jpg",
            ...     social={"twitter": "janesmith", "github": "janesmith"},
            ... )
            >>> author.name
            'Jane Smith'
            >>> author.social.get("twitter")
            'janesmith'

    """

    name: str
    email: str = ""
    bio: str = ""
    avatar: str = ""
    url: str = ""
    # Social links as immutable tuple of tuples for hashability
    _social_items: tuple[tuple[str, str], ...] = field(default=(), repr=False)

    @property
    def social(self) -> dict[str, str]:
        """
        Get social links as dictionary.

        Returns:
            Dictionary mapping platform names to handles/URLs

        Example:
            {% if author.social.twitter %}
              <a href="https://twitter.com/{{ author.social.twitter }}">@{{ author.social.twitter }}</a>
            {% endif %}
        """
        return dict(self._social_items)

    @property
    def twitter(self) -> str:
        """Shortcut for Twitter handle."""
        return self.social.get("twitter", "")

    @property
    def github(self) -> str:
        """Shortcut for GitHub username."""
        return self.social.get("github", "")

    @property
    def linkedin(self) -> str:
        """Shortcut for LinkedIn profile."""
        return self.social.get("linkedin", "")

    @property
    def mastodon(self) -> str:
        """Shortcut for Mastodon handle."""
        return self.social.get("mastodon", "")

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for template context or serialization.

        Returns:
            Dictionary with author data
        """
        return {
            "name": self.name,
            "email": self.email,
            "bio": self.bio,
            "avatar": self.avatar,
            "url": self.url,
            "social": self.social,
        }

    @classmethod
    def from_frontmatter(cls, data: str | dict[str, Any]) -> Author:
        """
        Create Author from frontmatter data.

        Handles both string format (just name) and dict format (with details).

        Args:
            data: Author data from frontmatter (string or dict)

        Returns:
            Author instance

        Examples:
            >>> Author.from_frontmatter("Jane Smith")
            Author(name='Jane Smith', ...)

            >>> Author.from_frontmatter({
            ...     "name": "Jane Smith",
            ...     "email": "jane@example.com",
            ...     "social": {"twitter": "janesmith"},
            ... })
            Author(name='Jane Smith', email='jane@example.com', ...)
        """
        if isinstance(data, str):
            return cls(name=data)

        if not isinstance(data, dict):
            return cls(name=str(data))

        name = data.get("name", "")
        if not name:
            # Fall back to checking for alternative keys
            name = data.get("author", "") or data.get("display_name", "")

        # Convert social dict to tuple of tuples for frozen dataclass
        social_dict = data.get("social", {})
        social_items = tuple(sorted(social_dict.items())) if isinstance(social_dict, dict) else ()

        return cls(
            name=str(name),
            email=str(data.get("email", "")),
            bio=str(data.get("bio", "")),
            avatar=str(data.get("avatar", "")),
            url=str(data.get("url", "")),
            _social_items=social_items,
        )

    def __str__(self) -> str:
        """Return author name for string representation."""
        return self.name

    def __bool__(self) -> bool:
        """Author is truthy if name is set."""
        return bool(self.name)
