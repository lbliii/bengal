"""Tests for author view filters (AuthorView, author_view filter)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import bengal.rendering.template_functions.authors as authors_mod
from bengal.rendering.template_functions.authors import (
    AuthorView,
    author_view_filter,
    authors_filter,
)


@pytest.fixture(autouse=True)
def _reset_site_ref():
    """Ensure module-level _site_ref is clean for each test (xdist safety)."""
    old = authors_mod._site_ref
    authors_mod._site_ref = None
    yield
    authors_mod._site_ref = old


class TestAuthorViewFromPage:
    """Tests for AuthorView.from_page()."""

    def test_extracts_basic_properties(self) -> None:
        """Should extract name, bio, avatar from page."""
        page = MagicMock()
        page.title = "Jane Doe"
        page.href = "/authors/jane-doe/"
        page.params = {"author_name": "jane-doe"}
        page.metadata = {
            "bio": "Software engineer and writer.",
            "avatar": "/avatars/jane.jpg",
        }

        view = AuthorView.from_page(page)

        assert view.name == "Jane Doe"
        assert view.key == "jane-doe"
        assert view.bio == "Software engineer and writer."
        assert view.avatar == "/avatars/jane.jpg"

    def test_extracts_company_and_location(self) -> None:
        """Should extract company and location."""
        page = MagicMock()
        page.title = "Author"
        page.href = "/authors/author/"
        page.params = {}
        page.metadata = {
            "company": "TechCorp",
            "location": "San Francisco, CA",
        }

        view = AuthorView.from_page(page)

        assert view.company == "TechCorp"
        assert view.location == "San Francisco, CA"

    def test_extracts_social_links_from_nested_dict(self) -> None:
        """Should extract social links from nested social dict."""
        page = MagicMock()
        page.title = "Author"
        page.href = "/authors/author/"
        page.params = {}
        page.metadata = {
            "social": {
                "twitter": "@authorhandle",
                "linkedin": "author-linkedin",
                "website": "https://author.com",
                "email": "author@example.com",
            }
        }

        view = AuthorView.from_page(page)

        assert view.twitter == "authorhandle"  # @ should be stripped
        assert view.linkedin == "author-linkedin"
        assert view.website == "https://author.com"
        assert view.email == "author@example.com"

    def test_extracts_github_from_direct_property(self) -> None:
        """Should extract github from direct metadata property."""
        page = MagicMock()
        page.title = "Author"
        page.href = "/authors/author/"
        page.params = {}
        page.metadata = {"github": "authorhandle"}

        view = AuthorView.from_page(page)

        assert view.github == "authorhandle"

    def test_merges_with_site_data(self) -> None:
        """Should merge with site.data.authors registry."""
        page = MagicMock()
        page.title = "Jane"
        page.href = "/authors/jane/"
        page.params = {"author_name": "jane"}
        page.metadata = {}

        site_data = {
            "jane": {
                "name": "Jane Doe",
                "bio": "From registry",
                "github": "janedoe",
            }
        }

        view = AuthorView.from_page(page, site_data=site_data)

        assert view.name == "Jane Doe"
        assert view.bio == "From registry"
        assert view.github == "janedoe"

    def test_site_data_takes_precedence(self) -> None:
        """Should prefer site data over page metadata."""
        page = MagicMock()
        page.title = "Page Title"
        page.href = "/authors/jane/"
        page.params = {"author_name": "jane"}
        page.metadata = {"name": "Page Name", "bio": "Page bio"}

        site_data = {
            "jane": {
                "name": "Registry Name",
                "bio": "Registry bio",
            }
        }

        view = AuthorView.from_page(page, site_data=site_data)

        assert view.name == "Registry Name"
        assert view.bio == "Registry bio"

    def test_counts_posts_from_index(self) -> None:
        """Should count posts from author index."""
        page = MagicMock()
        page.title = "Jane"
        page.href = "/authors/jane/"
        page.params = {"author_name": "jane"}
        page.metadata = {}

        author_index = {
            "jane": ["ref1", "ref2", "ref3"],  # 3 posts
        }

        view = AuthorView.from_page(page, author_index=author_index)

        assert view.post_count == 3

    def test_handles_missing_metadata(self) -> None:
        """Should handle page with no metadata."""
        page = MagicMock()
        page.title = "Author"
        page.href = "/author/"
        page.params = None
        page.metadata = None

        view = AuthorView.from_page(page)

        assert view.name == "Author"
        assert view.bio == ""
        assert view.twitter == ""


class TestAuthorViewFromData:
    """Tests for AuthorView.from_data()."""

    def test_creates_from_registry_data(self) -> None:
        """Should create AuthorView from registry data."""
        data = {
            "name": "John Smith",
            "bio": "Backend developer",
            "avatar": "/avatars/john.jpg",
            "company": "DevCorp",
            "github": "johnsmith",
        }

        view = AuthorView.from_data("john", data)

        assert view.key == "john"
        assert view.name == "John Smith"
        assert view.bio == "Backend developer"
        assert view.avatar == "/avatars/john.jpg"
        assert view.company == "DevCorp"
        assert view.github == "johnsmith"
        assert view.href == "/authors/john/"

    def test_extracts_from_links_array(self) -> None:
        """Should extract social links from links array."""
        data = {
            "name": "Author",
            "links": [
                {"href": "https://github.com/authorname"},
                {"url": "https://twitter.com/authorhandle"},
            ],
        }

        view = AuthorView.from_data("author", data)

        assert view.github == "authorname"
        assert view.twitter == "authorhandle"

    def test_counts_posts_from_index(self) -> None:
        """Should count posts from author index."""
        data = {"name": "Author"}
        author_index = {"author": ["p1", "p2"]}

        view = AuthorView.from_data("author", data, author_index)

        assert view.post_count == 2


class TestAuthorsFilter:
    """Tests for authors_filter()."""

    def test_converts_list_of_pages(self) -> None:
        """Should convert list of author pages to AuthorViews."""
        page1 = MagicMock()
        page1.title = "Author 1"
        page1.href = "/authors/author-1/"
        page1.params = {"author_name": "author-1"}
        page1.metadata = {}

        page2 = MagicMock()
        page2.title = "Author 2"
        page2.href = "/authors/author-2/"
        page2.params = {"author_name": "author-2"}
        page2.metadata = {}

        result = authors_filter([page1, page2])

        assert len(result) == 2
        assert result[0].name == "Author 1"
        assert result[1].name == "Author 2"

    def test_returns_empty_for_none(self) -> None:
        """Should return empty list for None input."""
        result = authors_filter(None)
        assert result == []


class TestAuthorViewFilter:
    """Tests for author_view_filter()."""

    def test_converts_single_page(self) -> None:
        """Should convert single page to AuthorView."""
        page = MagicMock()
        page.title = "Single Author"
        page.href = "/authors/single/"
        page.params = {}
        page.metadata = {}

        result = author_view_filter(page)

        assert result is not None
        assert result.name == "Single Author"

    def test_returns_none_for_none_input(self) -> None:
        """Should return None for None input."""
        result = author_view_filter(None)
        assert result is None
