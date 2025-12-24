"""Tests for bengal.core.author module."""

from __future__ import annotations

from bengal.core.author import Author


class TestAuthorBasic:
    """Test basic Author functionality."""

    def test_author_from_string(self):
        """Author can be created from a simple string."""
        author = Author.from_frontmatter("Jane Smith")
        assert author.name == "Jane Smith"
        assert author.email == ""
        assert author.bio == ""
        assert author.avatar == ""
        assert author.social == {}

    def test_author_from_dict(self):
        """Author can be created from a dict with full details."""
        data = {
            "name": "Jane Smith",
            "email": "jane@example.com",
            "bio": "Python enthusiast",
            "avatar": "/images/jane.jpg",
            "url": "https://janesmith.dev",
            "social": {
                "twitter": "janesmith",
                "github": "janesmith",
            },
        }
        author = Author.from_frontmatter(data)
        assert author.name == "Jane Smith"
        assert author.email == "jane@example.com"
        assert author.bio == "Python enthusiast"
        assert author.avatar == "/images/jane.jpg"
        assert author.url == "https://janesmith.dev"
        assert author.social["twitter"] == "janesmith"
        assert author.social["github"] == "janesmith"

    def test_author_social_shortcuts(self):
        """Author provides shortcuts for common social platforms."""
        author = Author.from_frontmatter(
            {
                "name": "Jane",
                "social": {
                    "twitter": "janesmith",
                    "github": "janedev",
                    "linkedin": "janepro",
                    "mastodon": "@jane@mastodon.social",
                },
            }
        )
        assert author.twitter == "janesmith"
        assert author.github == "janedev"
        assert author.linkedin == "janepro"
        assert author.mastodon == "@jane@mastodon.social"

    def test_author_truthiness(self):
        """Author is truthy when name is set."""
        assert bool(Author(name="Jane"))
        assert not bool(Author(name=""))

    def test_author_str(self):
        """Author string representation is the name."""
        author = Author(name="Jane Smith")
        assert str(author) == "Jane Smith"

    def test_author_to_dict(self):
        """Author can be serialized to dict."""
        author = Author.from_frontmatter(
            {
                "name": "Jane",
                "email": "jane@example.com",
                "social": {"twitter": "jane"},
            }
        )
        d = author.to_dict()
        assert d["name"] == "Jane"
        assert d["email"] == "jane@example.com"
        assert d["social"]["twitter"] == "jane"

    def test_author_hashable(self):
        """Author is hashable (frozen dataclass)."""
        author1 = Author(name="Jane")
        author2 = Author(name="Jane")
        # Should be hashable
        assert hash(author1) == hash(author2)
        # Should work in sets
        authors = {author1, author2}
        assert len(authors) == 1


class TestAuthorEdgeCases:
    """Test edge cases for Author parsing."""

    def test_author_empty_dict(self):
        """Empty dict returns Author with empty name."""
        author = Author.from_frontmatter({})
        assert author.name == ""

    def test_author_missing_name(self):
        """Dict without name still creates Author."""
        author = Author.from_frontmatter({"email": "test@test.com"})
        assert author.name == ""
        assert author.email == "test@test.com"

    def test_author_non_dict_non_string(self):
        """Non-dict/string value is converted to string."""
        author = Author.from_frontmatter(123)
        assert author.name == "123"

    def test_author_social_non_dict(self):
        """Non-dict social value is handled gracefully."""
        author = Author.from_frontmatter(
            {
                "name": "Jane",
                "social": "not a dict",
            }
        )
        assert author.social == {}


