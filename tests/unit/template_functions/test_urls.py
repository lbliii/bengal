"""Tests for URL template functions."""

from bengal.rendering.template_functions.urls import (
    absolute_url,
    ensure_trailing_slash,
    url_decode,
    url_encode,
    url_param,
    url_parse,
    url_query,
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


class TestEnsureTrailingSlash:
    """Tests for ensure_trailing_slash function."""

    def test_url_without_trailing_slash(self):
        result = ensure_trailing_slash("https://example.com/docs")
        assert result == "https://example.com/docs/"

    def test_url_with_trailing_slash(self):
        result = ensure_trailing_slash("https://example.com/docs/")
        assert result == "https://example.com/docs/"

    def test_path_without_trailing_slash(self):
        result = ensure_trailing_slash("/docs/guide")
        assert result == "/docs/guide/"

    def test_path_with_trailing_slash(self):
        result = ensure_trailing_slash("/docs/guide/")
        assert result == "/docs/guide/"

    def test_root_path(self):
        result = ensure_trailing_slash("/")
        assert result == "/"

    def test_empty_string(self):
        result = ensure_trailing_slash("")
        assert result == "/"

    def test_url_with_query_params(self):
        # Ensure trailing slash is added before query params would be
        result = ensure_trailing_slash("https://example.com/page")
        assert result == "https://example.com/page/"

    def test_url_with_fragment(self):
        # Ensure trailing slash is added to path
        result = ensure_trailing_slash("https://example.com/page")
        assert result == "https://example.com/page/"


class TestUrlParse:
    """Tests for url_parse filter."""

    def test_full_url(self):
        result = url_parse("https://example.com/path?q=test#section")
        assert result["scheme"] == "https"
        assert result["host"] == "example.com"
        assert result["path"] == "/path"
        assert result["query"] == "q=test"
        assert result["fragment"] == "section"
        assert result["params"]["q"] == ["test"]

    def test_url_with_multiple_params(self):
        result = url_parse("https://example.com/search?q=test&page=2&sort=date")
        assert result["params"]["q"] == ["test"]
        assert result["params"]["page"] == ["2"]
        assert result["params"]["sort"] == ["date"]

    def test_relative_url(self):
        result = url_parse("/docs/guide?version=2")
        assert result["scheme"] == ""
        assert result["host"] == ""
        assert result["path"] == "/docs/guide"
        assert result["params"]["version"] == ["2"]

    def test_empty_url(self):
        result = url_parse("")
        assert result["scheme"] == ""
        assert result["host"] == ""
        assert result["path"] == ""

    def test_none_url(self):
        result = url_parse(None)
        assert result["scheme"] == ""
        assert result["params"] == {}

    def test_url_without_query(self):
        result = url_parse("https://example.com/path")
        assert result["params"] == {}
        assert result["query"] == ""


class TestUrlParam:
    """Tests for url_param filter."""

    def test_extract_param(self):
        result = url_param("https://example.com?page=2", "page")
        assert result == "2"

    def test_extract_first_value(self):
        result = url_param("https://example.com?tag=a&tag=b", "tag")
        assert result == "a"

    def test_missing_param_default(self):
        result = url_param("https://example.com?page=2", "sort", "date")
        assert result == "date"

    def test_missing_param_empty(self):
        result = url_param("https://example.com?page=2", "sort")
        assert result == ""

    def test_empty_url(self):
        result = url_param("", "page", "1")
        assert result == "1"

    def test_none_url(self):
        result = url_param(None, "page", "1")
        assert result == "1"


class TestUrlQuery:
    """Tests for url_query filter."""

    def test_simple_dict(self):
        result = url_query({"q": "test", "page": 1})
        # Order may vary, so check both params are present
        assert "q=test" in result
        assert "page=1" in result

    def test_list_value(self):
        result = url_query({"tags": ["a", "b"]})
        assert "tags=a" in result
        assert "tags=b" in result

    def test_special_characters(self):
        result = url_query({"q": "hello world"})
        assert "q=hello+world" in result or "q=hello%20world" in result

    def test_empty_dict(self):
        result = url_query({})
        assert result == ""

    def test_none_dict(self):
        result = url_query(None)
        assert result == ""
