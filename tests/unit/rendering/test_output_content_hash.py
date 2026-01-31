"""
Tests for content hash embedding in output.py.

RFC: Output Cache Architecture - Tests embed_content_hash() and extract_content_hash()
functions for accurate change detection during hot reload.
"""

from __future__ import annotations

import pytest

from bengal.rendering.pipeline.output import embed_content_hash, extract_content_hash


class TestEmbedContentHash:
    """Tests for embed_content_hash function."""

    def test_embed_computes_hash_from_content(self) -> None:
        """Hash is computed from HTML content when not provided."""
        html = "<html><head></head><body>Test</body></html>"
        result = embed_content_hash(html)

        # Should contain meta tag
        assert 'name="bengal:content-hash"' in result
        assert "content=" in result

    def test_embed_uses_provided_hash(self) -> None:
        """Uses provided hash instead of computing."""
        html = "<html><head></head><body>Test</body></html>"
        result = embed_content_hash(html, content_hash="abc123def456")

        assert 'content="abc123def456"' in result

    def test_embed_inserts_after_head_tag(self) -> None:
        """Meta tag is inserted right after <head> tag."""
        html = "<html><head><title>Test</title></head><body></body></html>"
        result = embed_content_hash(html, content_hash="test123")

        # Tag should be between <head> and <title>
        head_pos = result.find("<head>")
        meta_pos = result.find('name="bengal:content-hash"')
        title_pos = result.find("<title>")

        assert head_pos < meta_pos < title_pos

    def test_embed_handles_head_with_attributes(self) -> None:
        """Works with <head> tags that have attributes."""
        html = '<html><head lang="en" class="test"></head></html>'
        result = embed_content_hash(html, content_hash="test123")

        assert 'content="test123"' in result

    def test_embed_case_insensitive_head(self) -> None:
        """Handles case variations of HEAD tag."""
        html = "<html><HEAD></HEAD></html>"
        result = embed_content_hash(html, content_hash="test123")

        assert 'content="test123"' in result

    def test_embed_returns_unchanged_without_head(self) -> None:
        """Returns unchanged HTML if no <head> tag found."""
        html = "<html><body>No head tag</body></html>"
        result = embed_content_hash(html, content_hash="test123")

        # Should return unchanged
        assert result == html

    def test_embed_replaces_existing_hash(self) -> None:
        """Replaces existing hash with new one."""
        # Note: Hashes must be valid hex (a-f0-9)
        html = """<html><head>
    <meta name="bengal:content-hash" content="abc123def456">
</head></html>"""
        result = embed_content_hash(html, content_hash="fedcba654321")

        # Should only have new hash
        assert 'content="fedcba654321"' in result
        assert 'content="abc123def456"' not in result
        # Only one hash meta tag
        assert result.count("bengal:content-hash") == 1


class TestExtractContentHash:
    """Tests for extract_content_hash function."""

    def test_extract_returns_hash(self) -> None:
        """Extracts hash from meta tag."""
        html = """<html><head>
    <meta name="bengal:content-hash" content="abc123def456">
</head></html>"""
        result = extract_content_hash(html)

        assert result == "abc123def456"

    def test_extract_handles_content_first(self) -> None:
        """Handles alternate attribute order (content before name)."""
        html = """<html><head>
    <meta content="abc123def456" name="bengal:content-hash">
</head></html>"""
        result = extract_content_hash(html)

        assert result == "abc123def456"

    def test_extract_returns_none_if_missing(self) -> None:
        """Returns None if no hash meta tag."""
        html = "<html><head></head></html>"
        result = extract_content_hash(html)

        assert result is None

    def test_extract_case_insensitive(self) -> None:
        """Handles case variations."""
        html = """<html><head>
    <META NAME="bengal:content-hash" CONTENT="abc123">
</head></html>"""
        result = extract_content_hash(html)

        assert result == "abc123"

    def test_extract_handles_whitespace(self) -> None:
        """Handles various whitespace in attributes."""
        html = """<html><head>
    <meta   name="bengal:content-hash"   content="abc123"  >
</head></html>"""
        result = extract_content_hash(html)

        assert result == "abc123"


class TestContentHashRoundtrip:
    """Tests for embed/extract roundtrip."""

    def test_roundtrip_preserves_hash(self) -> None:
        """Embedded hash can be extracted."""
        html = "<html><head></head><body>Test</body></html>"
        test_hash = "abc123def456"

        embedded = embed_content_hash(html, content_hash=test_hash)
        extracted = extract_content_hash(embedded)

        assert extracted == test_hash

    def test_deterministic_hash(self) -> None:
        """Same content produces same hash."""
        html = "<html><head></head><body>Hello World</body></html>"

        result1 = embed_content_hash(html)
        result2 = embed_content_hash(html)

        hash1 = extract_content_hash(result1)
        hash2 = extract_content_hash(result2)

        assert hash1 == hash2

    def test_different_content_different_hash(self) -> None:
        """Different content produces different hash."""
        html1 = "<html><head></head><body>Content A</body></html>"
        html2 = "<html><head></head><body>Content B</body></html>"

        result1 = embed_content_hash(html1)
        result2 = embed_content_hash(html2)

        hash1 = extract_content_hash(result1)
        hash2 = extract_content_hash(result2)

        assert hash1 != hash2
