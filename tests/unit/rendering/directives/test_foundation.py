"""
Tests for directive system v2 foundation classes.

Tests DirectiveToken, DirectiveOptions, and utility functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from bengal.rendering.plugins.directives import (
    ContainerOptions,
    DirectiveOptions,
    DirectiveToken,
    StyledOptions,
    TitledOptions,
    attr_str,
    bool_attr,
    build_class_string,
    class_attr,
    data_attrs,
    escape_html,
)

# =============================================================================
# DirectiveToken Tests
# =============================================================================


class TestDirectiveToken:
    """Tests for DirectiveToken dataclass."""

    def test_basic_token_creation(self) -> None:
        """Test creating a basic token with all fields."""
        token = DirectiveToken(
            type="dropdown",
            attrs={"title": "Details", "open": True},
            children=[{"type": "paragraph"}],
        )

        assert token.type == "dropdown"
        assert token.attrs == {"title": "Details", "open": True}
        assert token.children == [{"type": "paragraph"}]

    def test_default_values(self) -> None:
        """Test that attrs and children default to empty."""
        token = DirectiveToken(type="note")

        assert token.type == "note"
        assert token.attrs == {}
        assert token.children == []

    def test_to_dict(self) -> None:
        """Test conversion to mistune-compatible dict."""
        token = DirectiveToken(
            type="dropdown",
            attrs={"title": "Details"},
            children=[{"type": "paragraph", "text": "Content"}],
        )

        result = token.to_dict()

        assert result == {
            "type": "dropdown",
            "attrs": {"title": "Details"},
            "children": [{"type": "paragraph", "text": "Content"}],
        }

    def test_from_dict(self) -> None:
        """Test creating token from dict."""
        data = {
            "type": "step",
            "attrs": {"title": "Step 1"},
            "children": [],
        }

        token = DirectiveToken.from_dict(data)

        assert token.type == "step"
        assert token.attrs == {"title": "Step 1"}
        assert token.children == []

    def test_from_dict_missing_optionals(self) -> None:
        """Test from_dict with minimal data."""
        data = {"type": "note"}

        token = DirectiveToken.from_dict(data)

        assert token.type == "note"
        assert token.attrs == {}
        assert token.children == []

    def test_with_attrs(self) -> None:
        """Test adding attributes via with_attrs."""
        token = DirectiveToken(type="card", attrs={"title": "Card"})
        new_token = token.with_attrs(icon="star", link="/about")

        # Original unchanged
        assert token.attrs == {"title": "Card"}

        # New token has merged attrs
        assert new_token.attrs == {"title": "Card", "icon": "star", "link": "/about"}
        assert new_token.type == "card"

    def test_with_attrs_overwrite(self) -> None:
        """Test that with_attrs can overwrite existing values."""
        token = DirectiveToken(type="note", attrs={"title": "Old"})
        new_token = token.with_attrs(title="New")

        assert new_token.attrs == {"title": "New"}

    def test_with_children(self) -> None:
        """Test replacing children via with_children."""
        token = DirectiveToken(type="steps", children=[{"type": "step"}])
        new_children = [{"type": "step"}, {"type": "step"}]
        new_token = token.with_children(new_children)

        # Original unchanged
        assert len(token.children) == 1

        # New token has new children
        assert len(new_token.children) == 2


# =============================================================================
# DirectiveOptions Tests
# =============================================================================


class TestDirectiveOptions:
    """Tests for DirectiveOptions base class."""

    def test_basic_parsing(self) -> None:
        """Test basic option parsing."""

        @dataclass
        class TestOptions(DirectiveOptions):
            title: str = ""
            count: int = 0

        opts = TestOptions.from_raw({"title": "Hello", "count": "42"})

        assert opts.title == "Hello"
        assert opts.count == 42

    def test_bool_coercion(self) -> None:
        """Test bool type coercion from various string values."""

        @dataclass
        class TestOptions(DirectiveOptions):
            flag: bool = False

        # Truthy values
        assert TestOptions.from_raw({"flag": "true"}).flag is True
        assert TestOptions.from_raw({"flag": "True"}).flag is True
        assert TestOptions.from_raw({"flag": "TRUE"}).flag is True
        assert TestOptions.from_raw({"flag": "1"}).flag is True
        assert TestOptions.from_raw({"flag": "yes"}).flag is True
        assert TestOptions.from_raw({"flag": ""}).flag is True  # Empty = True

        # Falsy values
        assert TestOptions.from_raw({"flag": "false"}).flag is False
        assert TestOptions.from_raw({"flag": "0"}).flag is False
        assert TestOptions.from_raw({"flag": "no"}).flag is False

    def test_int_coercion(self) -> None:
        """Test int type coercion."""

        @dataclass
        class TestOptions(DirectiveOptions):
            count: int = 0

        assert TestOptions.from_raw({"count": "42"}).count == 42
        assert TestOptions.from_raw({"count": "-5"}).count == -5
        assert TestOptions.from_raw({"count": "invalid"}).count == 0  # Default on error

    def test_float_coercion(self) -> None:
        """Test float type coercion."""

        @dataclass
        class TestOptions(DirectiveOptions):
            ratio: float = 0.0

        assert TestOptions.from_raw({"ratio": "3.14"}).ratio == 3.14
        assert TestOptions.from_raw({"ratio": "-1.5"}).ratio == -1.5
        assert TestOptions.from_raw({"ratio": "invalid"}).ratio == 0.0

    def test_list_coercion(self) -> None:
        """Test list type coercion from comma-separated values."""

        @dataclass
        class TestOptions(DirectiveOptions):
            items: list[str] = None  # type: ignore

            def __post_init__(self) -> None:
                if self.items is None:
                    self.items = []

        opts = TestOptions.from_raw({"items": "a, b, c"})
        assert opts.items == ["a", "b", "c"]

        opts = TestOptions.from_raw({"items": "single"})
        assert opts.items == ["single"]

    def test_field_aliases(self) -> None:
        """Test field alias mapping (e.g., :class: -> css_class)."""

        @dataclass
        class TestOptions(DirectiveOptions):
            css_class: str = ""

            _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}

        opts = TestOptions.from_raw({"class": "my-class"})
        assert opts.css_class == "my-class"

    def test_hyphen_to_underscore(self) -> None:
        """Test automatic hyphen-to-underscore conversion in option names."""

        @dataclass
        class TestOptions(DirectiveOptions):
            max_width: str = ""

        opts = TestOptions.from_raw({"max-width": "100px"})
        assert opts.max_width == "100px"

    def test_allowed_values_valid(self) -> None:
        """Test allowed values validation - valid value."""

        @dataclass
        class TestOptions(DirectiveOptions):
            size: str = "medium"

            _allowed_values: ClassVar[dict[str, list[str]]] = {
                "size": ["small", "medium", "large"],
            }

        opts = TestOptions.from_raw({"size": "small"})
        assert opts.size == "small"

    def test_allowed_values_invalid(self) -> None:
        """Test allowed values validation - invalid value uses default."""

        @dataclass
        class TestOptions(DirectiveOptions):
            size: str = "medium"

            _allowed_values: ClassVar[dict[str, list[str]]] = {
                "size": ["small", "medium", "large"],
            }

        # Invalid value should be ignored, keeping default
        opts = TestOptions.from_raw({"size": "xlarge"})
        assert opts.size == "medium"

    def test_unknown_options_ignored(self) -> None:
        """Test that unknown options are ignored gracefully."""

        @dataclass
        class TestOptions(DirectiveOptions):
            known: str = ""

        # Should not raise, unknown option ignored
        opts = TestOptions.from_raw({"known": "value", "unknown": "ignored"})
        assert opts.known == "value"

    def test_default_values(self) -> None:
        """Test that defaults are used when options not provided."""

        @dataclass
        class TestOptions(DirectiveOptions):
            title: str = "Default Title"
            count: int = 10

        opts = TestOptions.from_raw({})
        assert opts.title == "Default Title"
        assert opts.count == 10


class TestPresetOptions:
    """Tests for preset option classes."""

    def test_styled_options(self) -> None:
        """Test StyledOptions preset."""
        opts = StyledOptions.from_raw({"class": "custom-class"})
        assert opts.css_class == "custom-class"

    def test_container_options(self) -> None:
        """Test ContainerOptions preset."""
        opts = ContainerOptions.from_raw(
            {
                "class": "grid-container",
                "columns": "3",
                "gap": "large",
                "style": "bordered",
            }
        )

        assert opts.css_class == "grid-container"
        assert opts.columns == "3"
        assert opts.gap == "large"
        assert opts.style == "bordered"

    def test_container_options_defaults(self) -> None:
        """Test ContainerOptions defaults."""
        opts = ContainerOptions.from_raw({})

        assert opts.css_class == ""
        assert opts.columns == "auto"
        assert opts.gap == "medium"
        assert opts.style == "default"

    def test_container_options_invalid_gap(self) -> None:
        """Test ContainerOptions with invalid gap value."""
        opts = ContainerOptions.from_raw({"gap": "invalid"})

        # Invalid value should fall back to default
        assert opts.gap == "medium"

    def test_titled_options(self) -> None:
        """Test TitledOptions preset."""
        opts = TitledOptions.from_raw({"class": "card", "icon": "star"})

        assert opts.css_class == "card"
        assert opts.icon == "star"


# =============================================================================
# Utility Function Tests
# =============================================================================


class TestEscapeHtml:
    """Tests for escape_html utility."""

    def test_basic_escaping(self) -> None:
        """Test basic HTML character escaping."""
        assert escape_html("<script>") == "&lt;script&gt;"
        assert escape_html('"quoted"') == "&quot;quoted&quot;"
        assert escape_html("'apostrophe'") == "&#x27;apostrophe&#x27;"
        assert escape_html("a & b") == "a &amp; b"

    def test_combined_escaping(self) -> None:
        """Test escaping multiple special characters."""
        result = escape_html('<a href="test">')
        assert result == "&lt;a href=&quot;test&quot;&gt;"

    def test_empty_string(self) -> None:
        """Test that empty string returns empty string."""
        assert escape_html("") == ""

    def test_no_escaping_needed(self) -> None:
        """Test string with no special characters."""
        assert escape_html("Hello World") == "Hello World"


class TestBuildClassString:
    """Tests for build_class_string utility."""

    def test_single_class(self) -> None:
        """Test with single class."""
        assert build_class_string("dropdown") == "dropdown"

    def test_multiple_classes(self) -> None:
        """Test with multiple classes."""
        assert build_class_string("dropdown", "open") == "dropdown open"

    def test_filters_empty(self) -> None:
        """Test that empty strings are filtered out."""
        assert build_class_string("dropdown", "", "custom") == "dropdown custom"

    def test_all_empty(self) -> None:
        """Test with all empty strings."""
        assert build_class_string("", "") == ""

    def test_strips_whitespace(self) -> None:
        """Test that whitespace is stripped."""
        assert build_class_string(" dropdown ", "  open  ") == "dropdown open"


class TestBoolAttr:
    """Tests for bool_attr utility."""

    def test_true_value(self) -> None:
        """Test with True value."""
        assert bool_attr("open", True) == " open"
        assert bool_attr("disabled", True) == " disabled"

    def test_false_value(self) -> None:
        """Test with False value."""
        assert bool_attr("open", False) == ""
        assert bool_attr("disabled", False) == ""


class TestDataAttrs:
    """Tests for data_attrs utility."""

    def test_basic_attrs(self) -> None:
        """Test basic data attribute generation."""
        result = data_attrs(columns="3", gap="medium")
        assert 'data-columns="3"' in result
        assert 'data-gap="medium"' in result

    def test_underscore_to_hyphen(self) -> None:
        """Test underscore to hyphen conversion."""
        result = data_attrs(max_width="100px")
        assert 'data-max-width="100px"' in result

    def test_filters_none(self) -> None:
        """Test that None values are filtered."""
        result = data_attrs(visible="true", hidden=None)
        assert "data-visible" in result
        assert "data-hidden" not in result

    def test_filters_empty_string(self) -> None:
        """Test that empty strings are filtered."""
        result = data_attrs(visible="true", empty="")
        assert "data-visible" in result
        assert "data-empty" not in result

    def test_escapes_values(self) -> None:
        """Test that values are HTML-escaped."""
        result = data_attrs(title='Click "here"')
        assert 'data-title="Click &quot;here&quot;"' in result


class TestAttrStr:
    """Tests for attr_str utility."""

    def test_with_value(self) -> None:
        """Test with non-empty value."""
        assert attr_str("href", "https://example.com") == ' href="https://example.com"'

    def test_with_none(self) -> None:
        """Test with None value."""
        assert attr_str("href", None) == ""

    def test_with_empty_string(self) -> None:
        """Test with empty string value."""
        assert attr_str("href", "") == ""

    def test_escapes_value(self) -> None:
        """Test that value is HTML-escaped."""
        assert attr_str("title", 'Say "Hello"') == ' title="Say &quot;Hello&quot;"'


class TestClassAttr:
    """Tests for class_attr utility."""

    def test_with_classes(self) -> None:
        """Test with classes."""
        assert class_attr("dropdown", "open") == ' class="dropdown open"'

    def test_single_class(self) -> None:
        """Test with single class."""
        assert class_attr("dropdown") == ' class="dropdown"'

    def test_empty_classes(self) -> None:
        """Test with all empty classes."""
        assert class_attr("", "") == ""
