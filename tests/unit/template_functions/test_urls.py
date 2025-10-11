"""Tests for URL template functions."""

from bengal.rendering.template_functions.urls import (
    absolute_url,
    url_encode,
    url_decode,
)


class TestAbsoluteUrl:
    """Tests for absolute_url filter."""
    
    def test_relative_url(self):
        result = absolute_url("/posts/my-post/", "https://example.com")
        assert result == "https://example.com/posts/my-post/"
    
    def test_already_absolute(self):
        url = "https://other.com/page/"
        result = absolute_url(url, "https://example.com")
        assert result == url
    
    def test_protocol_relative(self):
        url = "//cdn.example.com/file.js"
        result = absolute_url(url, "https://example.com")
        assert result == url
    
    def test_no_base_url(self):
        result = absolute_url("/posts/", "")
        assert result == "/posts/"
    
    def test_empty_url(self):
        result = absolute_url("", "https://example.com")
        assert result == "https://example.com"
    
    def test_url_without_leading_slash(self):
        result = absolute_url("posts/my-post/", "https://example.com")
        assert result == "https://example.com/posts/my-post/"
    
    def test_base_url_with_trailing_slash(self):
        result = absolute_url("/posts/", "https://example.com/")
        assert result == "https://example.com/posts/"


class TestUrlEncode:
    """Tests for url_encode filter."""
    
    def test_encode_spaces(self):
        result = url_encode("hello world")
        assert result == "hello%20world"
    
    def test_encode_special_chars(self):
        result = url_encode("hello@world.com")
        assert "%40" in result  # @ encoded
    
    def test_encode_unicode(self):
        result = url_encode("héllo")
        assert "h" in result
        # Should encode é
        assert "%" in result
    
    def test_empty_string(self):
        assert url_encode("") == ""
    
    def test_already_encoded(self):
        result = url_encode("hello")
        assert result == "hello"


class TestUrlDecode:
    """Tests for url_decode filter."""
    
    def test_decode_spaces(self):
        result = url_decode("hello%20world")
        assert result == "hello world"
    
    def test_decode_special_chars(self):
        result = url_decode("hello%40world.com")
        assert result == "hello@world.com"
    
    def test_decode_plus(self):
        result = url_decode("hello+world")
        assert result == "hello+world"  # unquote doesn't convert + to space
    
    def test_empty_string(self):
        assert url_decode("") == ""
    
    def test_no_encoding(self):
        result = url_decode("hello")
        assert result == "hello"

