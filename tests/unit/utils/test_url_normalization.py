"""
Tests for URL normalization utilities.
"""

from bengal.utils.paths.url_normalization import (
    clean_md_path,
    join_url_paths,
    normalize_url,
    path_to_slug,
    split_url_path,
    validate_url,
)


class TestNormalizeUrl:
    """Tests for normalize_url function."""

    def test_basic_normalization(self):
        """Test basic URL normalization."""
        assert normalize_url("api/bengal") == "/api/bengal/"
        assert normalize_url("/api/bengal") == "/api/bengal/"
        assert normalize_url("api/bengal/") == "/api/bengal/"

    def test_multiple_slashes(self):
        """Test normalization of multiple slashes."""
        assert normalize_url("/api//bengal/") == "/api/bengal/"
        assert normalize_url("///api///bengal///") == "/api/bengal/"

    def test_root_url(self):
        """Test root URL handling."""
        assert normalize_url("") == "/"
        assert normalize_url("/") == "/"

    def test_trailing_slash_option(self):
        """Test ensure_trailing_slash option."""
        assert normalize_url("/api/bengal", ensure_trailing_slash=True) == "/api/bengal/"
        assert normalize_url("/api/bengal", ensure_trailing_slash=False) == "/api/bengal"
        assert normalize_url("/api/bengal/", ensure_trailing_slash=False) == "/api/bengal"

    def test_absolute_urls_unchanged(self):
        """Test that absolute URLs are not modified."""
        assert normalize_url("http://example.com/path") == "http://example.com/path"
        assert normalize_url("https://example.com/path") == "https://example.com/path"
        assert normalize_url("//example.com/path") == "//example.com/path"


class TestJoinUrlPaths:
    """Tests for join_url_paths function."""

    def test_basic_join(self):
        """Test basic path joining."""
        assert join_url_paths("/api", "bengal") == "/api/bengal/"
        assert join_url_paths("api", "bengal", "core") == "/api/bengal/core/"

    def test_with_slashes(self):
        """Test joining paths with slashes."""
        assert join_url_paths("/api/", "/bengal/") == "/api/bengal/"
        assert join_url_paths("/api/", "bengal/") == "/api/bengal/"

    def test_empty_parts(self):
        """Test joining with empty parts."""
        assert join_url_paths("/api", "", "bengal") == "/api/bengal/"
        assert join_url_paths("", "", "") == "/"

    def test_single_part(self):
        """Test joining single part."""
        assert join_url_paths("api") == "/api/"
        assert join_url_paths("/api/") == "/api/"


class TestValidateUrl:
    """Tests for validate_url function."""

    def test_valid_urls(self):
        """Test valid URLs."""
        assert validate_url("/") is True
        assert validate_url("/api/") is True
        assert validate_url("/api/bengal/core/") is True

    def test_invalid_urls(self):
        """Test invalid URLs."""
        assert validate_url("") is False
        assert validate_url("api/") is False  # No leading slash
        assert validate_url("//double//slashes//") is False


class TestSplitUrlPath:
    """Tests for split_url_path function."""

    def test_basic_split(self):
        """Test basic URL path splitting."""
        assert split_url_path("/api/bengal/core/") == ["api", "bengal", "core"]
        assert split_url_path("api/bengal") == ["api", "bengal"]

    def test_root_path(self):
        """Test root path splitting."""
        assert split_url_path("/") == []
        assert split_url_path("") == []

    def test_single_segment(self):
        """Test single segment path."""
        assert split_url_path("single") == ["single"]
        assert split_url_path("/single/") == ["single"]

    def test_leading_trailing_slashes(self):
        """Test handling of leading/trailing slashes."""
        assert split_url_path("/api/") == ["api"]
        assert split_url_path("api/") == ["api"]
        assert split_url_path("/api") == ["api"]

    def test_deep_path(self):
        """Test deep nested path."""
        assert split_url_path("/a/b/c/d/e/") == ["a", "b", "c", "d", "e"]


class TestCleanMdPath:
    """Tests for clean_md_path function."""

    def test_basic_cleaning(self):
        """Test basic .md removal."""
        assert clean_md_path("docs/guide.md") == "docs/guide"
        assert clean_md_path("README.md") == "README"

    def test_no_md_extension(self):
        """Test path without .md extension."""
        assert clean_md_path("docs/guide") == "docs/guide"
        assert clean_md_path("api/reference") == "api/reference"

    def test_strip_slashes(self):
        """Test stripping of leading/trailing slashes."""
        assert clean_md_path("/docs/guide.md/") == "docs/guide"
        assert clean_md_path("/api/reference/") == "api/reference"

    def test_multiple_md(self):
        """Test multiple .md occurrences."""
        # Only the .md extension should be removed
        assert clean_md_path("docs.md/guide.md") == "docs/guide"

    def test_empty_string(self):
        """Test empty string."""
        assert clean_md_path("") == ""
        assert clean_md_path("/") == ""


class TestPathToSlug:
    """Tests for path_to_slug function."""

    def test_basic_conversion(self):
        """Test basic path to slug conversion."""
        assert path_to_slug("/api/bengal/core/") == "api-bengal-core"
        assert path_to_slug("api/bengal") == "api-bengal"

    def test_root_path(self):
        """Test root path conversion."""
        assert path_to_slug("/") == ""
        assert path_to_slug("") == ""

    def test_single_segment(self):
        """Test single segment path."""
        assert path_to_slug("single") == "single"
        assert path_to_slug("/single/") == "single"

    def test_deep_path(self):
        """Test deep nested path."""
        assert path_to_slug("/a/b/c/d/") == "a-b-c-d"

    def test_no_slashes(self):
        """Test path without slashes."""
        assert path_to_slug("filename") == "filename"
