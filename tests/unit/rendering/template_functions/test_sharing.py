"""Tests for bengal.rendering.template_functions.sharing module."""

from __future__ import annotations

from bengal.rendering.template_functions.sharing import (
    email_share_url,
    facebook_share_url,
    hackernews_share_url,
    linkedin_share_url,
    mastodon_share_text,
    reddit_share_url,
    share_url,
    twitter_share_url,
)


class TestTwitterShareUrl:
    """Test Twitter/X share URL generation."""

    def test_basic_url(self):
        """Twitter share URL with just URL."""
        url = twitter_share_url("https://example.com/post")
        assert "twitter.com/intent/tweet" in url
        assert "url=https" in url

    def test_with_text(self):
        """Twitter share URL with text."""
        url = twitter_share_url("https://example.com", text="Check this out!")
        assert "text=Check" in url

    def test_with_via(self):
        """Twitter share URL with via attribution."""
        url = twitter_share_url("https://example.com", via="myblog")
        assert "via=myblog" in url

    def test_via_strips_at(self):
        """Via parameter strips @ prefix."""
        url = twitter_share_url("https://example.com", via="@myblog")
        assert "via=myblog" in url
        assert "via=%40" not in url

    def test_with_hashtags(self):
        """Twitter share URL with hashtags."""
        url = twitter_share_url("https://example.com", hashtags=["python", "web"])
        assert "hashtags=python" in url


class TestLinkedInShareUrl:
    """Test LinkedIn share URL generation."""

    def test_basic_url(self):
        """LinkedIn share URL generation."""
        url = linkedin_share_url("https://example.com/article")
        assert "linkedin.com/sharing/share-offsite" in url
        assert "url=https" in url


class TestFacebookShareUrl:
    """Test Facebook share URL generation."""

    def test_basic_url(self):
        """Facebook share URL generation."""
        url = facebook_share_url("https://example.com/post")
        assert "facebook.com/sharer/sharer.php" in url
        assert "u=https" in url


class TestRedditShareUrl:
    """Test Reddit share URL generation."""

    def test_basic_url(self):
        """Reddit share URL with URL only."""
        url = reddit_share_url("https://example.com/post")
        assert "reddit.com/submit" in url
        assert "url=https" in url

    def test_with_title(self):
        """Reddit share URL with title."""
        url = reddit_share_url("https://example.com", title="My Post")
        assert "title=My" in url


class TestHackerNewsShareUrl:
    """Test Hacker News share URL generation."""

    def test_basic_url(self):
        """HN share URL with URL only."""
        url = hackernews_share_url("https://example.com/post")
        assert "news.ycombinator.com/submitlink" in url
        assert "u=https" in url

    def test_with_title(self):
        """HN share URL with title."""
        url = hackernews_share_url("https://example.com", title="My Post")
        assert "t=My" in url


class TestEmailShareUrl:
    """Test email share URL generation."""

    def test_basic_url(self):
        """Email share URL with URL only."""
        url = email_share_url("https://example.com/post")
        assert url.startswith("mailto:?")
        assert "body=https" in url

    def test_with_subject(self):
        """Email share URL with subject."""
        url = email_share_url("https://example.com", subject="Check this out")
        assert "subject=Check" in url


class TestMastodonShareText:
    """Test Mastodon share text generation."""

    def test_url_only(self):
        """Mastodon share text with URL only."""
        text = mastodon_share_text("https://example.com/post")
        assert text == "https://example.com/post"

    def test_with_text(self):
        """Mastodon share text with message."""
        text = mastodon_share_text("https://example.com", text="Check this out!")
        assert text == "Check this out! https://example.com"


class TestShareUrlDispatcher:
    """Test the share_url dispatcher function."""

    def test_twitter_dispatch(self):
        """share_url routes to Twitter correctly."""

        class MockPage:
            absolute_href = "https://example.com/post"
            title = "My Post"

        url = share_url("twitter", MockPage())
        assert "twitter.com" in url

    def test_x_alias(self):
        """share_url accepts 'x' as alias for Twitter."""

        class MockPage:
            absolute_href = "https://example.com/post"
            title = "My Post"

        url = share_url("x", MockPage())
        assert "twitter.com" in url

    def test_hn_alias(self):
        """share_url accepts 'hn' as alias for Hacker News."""

        class MockPage:
            absolute_href = "https://example.com/post"
            title = "My Post"

        url = share_url("hn", MockPage())
        assert "news.ycombinator.com" in url

    def test_unknown_platform(self):
        """share_url returns empty string for unknown platform."""

        class MockPage:
            absolute_href = "https://example.com/post"
            title = "My Post"

        url = share_url("unknown_platform", MockPage())
        assert url == ""

    def test_uses_href_fallback(self):
        """share_url falls back to href if absolute_href not available."""

        class MockPage:
            href = "https://example.com/post"
            title = "My Post"

        url = share_url("twitter", MockPage())
        assert "example.com" in url
