"""
Tests for directive utility functions.
"""

from bengal.directives.utils import (
    attr_str,
    bool_attr,
    build_class_string,
    class_attr,
    clean_soundcloud_path,
    data_attrs,
    ensure_badge_base_class,
    escape_html,
)


class TestEnsureBadgeBaseClass:
    """Tests for ensure_badge_base_class function."""

    def test_empty_class(self):
        """Test empty class input."""
        assert ensure_badge_base_class("") == "badge badge-secondary"

    def test_modifier_only(self):
        """Test modifier class without base."""
        assert ensure_badge_base_class("badge-primary") == "badge badge-primary"
        assert ensure_badge_base_class("badge-danger") == "badge badge-danger"
        assert ensure_badge_base_class("badge-secondary") == "badge badge-secondary"

    def test_base_already_present(self):
        """Test when base class is already present."""
        assert ensure_badge_base_class("badge badge-primary") == "badge badge-primary"
        assert ensure_badge_base_class("badge") == "badge"

    def test_api_badge_class(self):
        """Test api-badge class handling."""
        assert ensure_badge_base_class("api-badge-warning") == "api-badge api-badge-warning"
        assert ensure_badge_base_class("api-badge") == "api-badge"

    def test_custom_class(self):
        """Test custom class without badge prefix."""
        assert ensure_badge_base_class("custom-class") == "badge custom-class"
        assert ensure_badge_base_class("my-special-badge") == "badge my-special-badge"

    def test_multiple_classes(self):
        """Test multiple classes."""
        result = ensure_badge_base_class("badge-primary extra-class")
        assert result.startswith("badge ")
        assert "badge-primary" in result
        assert "extra-class" in result


class TestCleanSoundcloudPath:
    """Tests for clean_soundcloud_path function."""

    def test_full_url(self):
        """Test full SoundCloud URL."""
        assert clean_soundcloud_path("https://soundcloud.com/artist/song") == "artist/song"

    def test_domain_without_protocol(self):
        """Test URL without https://."""
        assert clean_soundcloud_path("soundcloud.com/artist/song") == "artist/song"

    def test_path_only(self):
        """Test path without domain."""
        assert clean_soundcloud_path("artist/song") == "artist/song"

    def test_with_query_params(self):
        """Test URL with query parameters."""
        assert clean_soundcloud_path("artist/song?si=abc") == "artist/song"
        assert clean_soundcloud_path("https://soundcloud.com/artist/song?ref=123") == "artist/song"

    def test_nested_path(self):
        """Test nested path (sets/playlists)."""
        assert clean_soundcloud_path("artist/sets/playlist-name") == "artist/sets/playlist-name"


class TestBuildClassString:
    """Tests for build_class_string function."""

    def test_basic_join(self):
        """Test basic class joining."""
        assert build_class_string("dropdown", "my-class") == "dropdown my-class"

    def test_empty_filtering(self):
        """Test empty class filtering."""
        assert build_class_string("dropdown", "", "my-class") == "dropdown my-class"
        assert build_class_string("", "") == ""

    def test_whitespace_stripping(self):
        """Test whitespace stripping."""
        assert build_class_string("base", "  extra  ", "") == "base extra"


class TestBoolAttr:
    """Tests for bool_attr function."""

    def test_true_value(self):
        """Test true value generates attribute."""
        assert bool_attr("open", True) == " open"
        assert bool_attr("disabled", True) == " disabled"

    def test_false_value(self):
        """Test false value generates nothing."""
        assert bool_attr("open", False) == ""
        assert bool_attr("disabled", False) == ""


class TestDataAttrs:
    """Tests for data_attrs function."""

    def test_basic_data_attrs(self):
        """Test basic data attribute generation."""
        result = data_attrs(columns="auto", gap="medium")
        assert 'data-columns="auto"' in result
        assert 'data-gap="medium"' in result

    def test_none_filtering(self):
        """Test None values are filtered."""
        result = data_attrs(count=3, empty="", none_val=None)
        assert 'data-count="3"' in result
        assert "data-empty" not in result
        assert "data-none-val" not in result

    def test_empty_attrs(self):
        """Test empty attrs returns empty string."""
        assert data_attrs() == ""


class TestAttrStr:
    """Tests for attr_str function."""

    def test_basic_attr(self):
        """Test basic attribute generation."""
        assert attr_str("href", "https://example.com") == ' href="https://example.com"'

    def test_none_value(self):
        """Test None value returns empty string."""
        assert attr_str("href", None) == ""

    def test_empty_value(self):
        """Test empty value returns empty string."""
        assert attr_str("href", "") == ""

    def test_escaping(self):
        """Test HTML escaping in attribute value."""
        assert attr_str("title", 'Say "Hello"') == ' title="Say &quot;Hello&quot;"'


class TestClassAttr:
    """Tests for class_attr function."""

    def test_basic_class_attr(self):
        """Test basic class attribute generation."""
        assert class_attr("dropdown", "open") == ' class="dropdown open"'

    def test_empty_classes(self):
        """Test empty classes returns empty string."""
        assert class_attr("", "") == ""

    def test_single_class(self):
        """Test single class."""
        assert class_attr("dropdown") == ' class="dropdown"'


class TestEscapeHtml:
    """Tests for escape_html function (re-exported)."""

    def test_basic_escaping(self):
        """Test basic HTML escaping."""
        assert escape_html("<script>") == "&lt;script&gt;"
        assert escape_html('"quotes"') == "&quot;quotes&quot;"
