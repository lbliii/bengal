"""
Unit tests for URL ownership system.

Tests URLRegistry, URLClaim, and URLCollisionError functionality.
"""

from __future__ import annotations

import pytest

from bengal.core.url_ownership import URLClaim, URLCollisionError, URLRegistry


class TestURLClaim:
    """Test URLClaim dataclass."""

    def test_url_claim_creation(self):
        """Test creating a URLClaim."""
        claim = URLClaim(
            owner="content",
            source="content/about.md",
            priority=100,
        )
        assert claim.owner == "content"
        assert claim.source == "content/about.md"
        assert claim.priority == 100
        assert claim.version is None
        assert claim.lang is None

    def test_url_claim_with_version_and_lang(self):
        """Test URLClaim with version and language."""
        claim = URLClaim(
            owner="content",
            source="content/about.md",
            priority=100,
            version="v2",
            lang="en",
        )
        assert claim.version == "v2"
        assert claim.lang == "en"

    def test_url_claim_str_representation(self):
        """Test URLClaim string representation."""
        claim = URLClaim(
            owner="content",
            source="content/about.md",
            priority=100,
        )
        assert "content" in str(claim)
        assert "priority 100" in str(claim)
        assert "content/about.md" in str(claim)


class TestURLRegistry:
    """Test URLRegistry functionality."""

    def test_registry_initialization(self):
        """Test registry starts empty."""
        registry = URLRegistry()
        assert len(registry.all_claims()) == 0

    def test_claim_single_url(self):
        """Test claiming a single URL."""
        registry = URLRegistry()
        registry.claim(
            url="/about/",
            owner="content",
            source="content/about.md",
            priority=100,
        )
        assert len(registry.all_claims()) == 1
        claim = registry.get_claim("/about/")
        assert claim is not None
        assert claim.owner == "content"
        assert claim.priority == 100

    def test_claim_normalizes_url(self):
        """Test that URLs are normalized (trailing slash, lowercase)."""
        registry = URLRegistry()
        registry.claim(
            url="/ABOUT",
            owner="content",
            source="content/about.md",
            priority=100,
        )
        # Should normalize to /about/
        claim = registry.get_claim("/about/")
        assert claim is not None
        assert claim.owner == "content"

    def test_claim_higher_priority_wins(self):
        """Test that higher priority claims override lower priority."""
        registry = URLRegistry()
        # Lower priority first
        registry.claim(
            url="/about/",
            owner="taxonomy",
            source="tags/about",
            priority=40,
        )
        # Higher priority overrides
        registry.claim(
            url="/about/",
            owner="content",
            source="content/about.md",
            priority=100,
        )
        claim = registry.get_claim("/about/")
        assert claim is not None
        assert claim.owner == "content"
        assert claim.priority == 100

    def test_claim_lower_priority_rejected(self):
        """Test that lower priority claims are rejected."""
        registry = URLRegistry()
        # Higher priority first
        registry.claim(
            url="/about/",
            owner="content",
            source="content/about.md",
            priority=100,
        )
        # Lower priority should be rejected
        with pytest.raises(URLCollisionError) as exc_info:
            registry.claim(
                url="/about/",
                owner="taxonomy",
                source="tags/about",
                priority=40,
            )
        assert "content" in str(exc_info.value)
        assert "taxonomy" in str(exc_info.value)

    def test_claim_same_priority_same_source_idempotent(self):
        """Test that same priority + same source is idempotent."""
        registry = URLRegistry()
        registry.claim(
            url="/about/",
            owner="content",
            source="content/about.md",
            priority=100,
        )
        # Same claim again should be allowed (idempotent)
        registry.claim(
            url="/about/",
            owner="content",
            source="content/about.md",
            priority=100,
        )
        assert len(registry.all_claims()) == 1

    def test_claim_same_priority_different_source_rejected(self):
        """Test that same priority with different source is rejected."""
        registry = URLRegistry()
        registry.claim(
            url="/about/",
            owner="content",
            source="content/about.md",
            priority=100,
        )
        # Same priority, different source should be rejected
        with pytest.raises(URLCollisionError):
            registry.claim(
                url="/about/",
                owner="content",
                source="content/about-v2.md",
                priority=100,
            )

    def test_claim_output_path(self, tmp_path):
        """Test claiming via output path."""

        from bengal.core.site import Site

        # Create a minimal site
        site = Site(root_path=tmp_path, config={"output_dir": "public"})
        registry = URLRegistry()
        site.url_registry = registry

        output_path = site.output_dir / "about" / "index.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        url = registry.claim_output_path(
            output_path=output_path,
            site=site,
            owner="content",
            source="content/about.md",
            priority=100,
        )
        assert url == "/about/"
        claim = registry.get_claim("/about/")
        assert claim is not None
        assert claim.owner == "content"

    def test_clear_registry(self):
        """Test clearing all claims."""
        registry = URLRegistry()
        registry.claim(
            url="/about/",
            owner="content",
            source="content/about.md",
            priority=100,
        )
        assert len(registry.all_claims()) == 1
        registry.clear()
        assert len(registry.all_claims()) == 0

    def test_to_dict_serialization(self):
        """Test serializing claims to dict."""
        registry = URLRegistry()
        registry.claim(
            url="/about/",
            owner="content",
            source="content/about.md",
            priority=100,
            version="v2",
            lang="en",
        )
        claims_dict = registry.to_dict()
        assert "/about/" in claims_dict
        assert claims_dict["/about/"]["owner"] == "content"
        assert claims_dict["/about/"]["priority"] == 100
        assert claims_dict["/about/"]["version"] == "v2"
        assert claims_dict["/about/"]["lang"] == "en"

    def test_load_from_dict(self):
        """Test loading claims from dict."""
        registry = URLRegistry()
        claims_dict = {
            "/about/": {
                "owner": "content",
                "source": "content/about.md",
                "priority": 100,
                "version": "v2",
                "lang": "en",
            }
        }
        registry.load_from_dict(claims_dict)
        claim = registry.get_claim("/about/")
        assert claim is not None
        assert claim.owner == "content"
        assert claim.priority == 100
        assert claim.version == "v2"
        assert claim.lang == "en"


class TestURLCollisionError:
    """Test URLCollisionError exception."""

    def test_collision_error_message(self):
        """Test collision error includes diagnostic information."""
        existing = URLClaim(
            owner="content",
            source="content/about.md",
            priority=100,
        )
        error = URLCollisionError(
            url="/about/",
            existing=existing,
            new_owner="taxonomy",
            new_source="tags/about",
            new_priority=40,
        )
        assert "/about/" in str(error)
        assert "content" in str(error)
        assert "taxonomy" in str(error)
        assert "100" in str(error)
        assert "40" in str(error)
