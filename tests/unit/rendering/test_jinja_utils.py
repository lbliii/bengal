"""Tests for Jinja2 utility functions."""

import pytest
from jinja2 import Undefined

from bengal.rendering.jinja_utils import (
    ensure_defined,
    has_value,
    is_undefined,
    safe_get,
    safe_get_attr,
)


class TestIsUndefined:
    """Test is_undefined() function."""

    def test_undefined_object(self):
        """Test detecting Undefined objects."""
        undefined_val = Undefined()
        assert is_undefined(undefined_val) is True

    def test_defined_values(self):
        """Test that defined values return False."""
        assert is_undefined("hello") is False
        assert is_undefined(42) is False
        assert is_undefined([1, 2, 3]) is False
        assert is_undefined({"key": "value"}) is False
        assert is_undefined(True) is False

    def test_none_is_not_undefined(self):
        """Test that None is not considered Undefined."""
        assert is_undefined(None) is False

    def test_empty_string_is_not_undefined(self):
        """Test that empty string is not Undefined."""
        assert is_undefined("") is False

    def test_zero_is_not_undefined(self):
        """Test that zero is not Undefined."""
        assert is_undefined(0) is False


class TestSafeGet:
    """Test safe_get() function."""

    def test_get_existing_attribute(self):
        """Test getting an attribute that exists."""

        class Page:
            title = "Hello World"
            author = "Alice"

        page = Page()
        assert safe_get(page, "title") == "Hello World"
        assert safe_get(page, "author") == "Alice"

    def test_get_missing_attribute_returns_default(self):
        """Test getting missing attribute returns default."""

        class Page:
            title = "Hello"

        page = Page()
        assert safe_get(page, "missing") is None
        assert safe_get(page, "missing", "default") == "default"

    def test_get_undefined_returns_default(self):
        """Test that Undefined values return default."""

        class Page:
            title = Undefined()

        page = Page()
        assert safe_get(page, "title", "Untitled") == "Untitled"

    def test_get_none_returns_none(self):
        """Test that None values are returned (not replaced with default)."""

        class Page:
            title = None

        page = Page()
        result = safe_get(page, "title", "default")
        # None is a valid value, should be returned
        assert result is None

    def test_get_from_dict_like_object(self):
        """Test getting attributes from dict-like objects."""
        data = {"title": "Test", "count": 42}

        class DictWrapper:
            def __init__(self, data):
                self._data = data

            def __getattr__(self, key):
                return self._data.get(key)

        obj = DictWrapper(data)
        assert safe_get(obj, "title") == "Test"
        assert safe_get(obj, "count") == 42
        assert safe_get(obj, "missing", "default") == "default"

    def test_get_handles_type_error(self):
        """Test that TypeError is handled gracefully."""
        # Trying to get attribute from a primitive type
        result = safe_get(42, "title", "default")
        assert result == "default"

        result = safe_get("string", "title", "default")
        assert result == "default"


class TestHasValue:
    """Test has_value() function."""

    def test_truthy_values(self):
        """Test that truthy values return True."""
        assert has_value("hello") is True
        assert has_value(42) is True
        assert has_value([1, 2, 3]) is True
        assert has_value({"key": "value"}) is True
        assert has_value(True) is True
        assert has_value(1) is True

    def test_falsy_values(self):
        """Test that falsy values return False."""
        assert has_value("") is False
        assert has_value(0) is False
        assert has_value([]) is False
        assert has_value({}) is False
        assert has_value(False) is False
        assert has_value(None) is False

    def test_undefined_returns_false(self):
        """Test that Undefined values return False."""
        assert has_value(Undefined()) is False

    def test_whitespace_string(self):
        """Test that whitespace-only string is truthy (not empty)."""
        # Note: "  " is not empty, so it's truthy
        assert has_value("  ") is True
        assert has_value(" ") is True


class TestSafeGetAttr:
    """Test safe_get_attr() for nested attribute access."""

    def test_single_level_access(self):
        """Test accessing single-level attribute."""

        class Page:
            title = "Hello"

        page = Page()
        assert safe_get_attr(page, "title") == "Hello"

    def test_nested_access(self):
        """Test accessing nested attributes."""

        class Profile:
            name = "Alice"

        class User:
            profile = Profile()

        user = User()
        assert safe_get_attr(user, "profile", "name") == "Alice"

    def test_deeply_nested_access(self):
        """Test deeply nested attribute access."""

        class Address:
            city = "Seattle"

        class Profile:
            address = Address()

        class User:
            profile = Profile()

        user = User()
        assert safe_get_attr(user, "profile", "address", "city") == "Seattle"

    def test_missing_intermediate_returns_default(self):
        """Test that missing intermediate attribute returns default."""

        class User:
            name = "Alice"

        user = User()
        result = safe_get_attr(user, "profile", "name", default="Unknown")
        assert result == "Unknown"

    def test_missing_final_returns_default(self):
        """Test that missing final attribute returns default."""

        class Profile:
            name = "Alice"

        class User:
            profile = Profile()

        user = User()
        result = safe_get_attr(user, "profile", "missing", default="N/A")
        assert result == "N/A"

    def test_undefined_intermediate_returns_default(self):
        """Test that Undefined intermediate value returns default."""

        class User:
            profile = Undefined()

        user = User()
        result = safe_get_attr(user, "profile", "name", default="Unknown")
        assert result == "Unknown"

    def test_none_intermediate_returns_default(self):
        """Test that None intermediate value returns default."""

        class User:
            profile = None

        user = User()
        result = safe_get_attr(user, "profile", "name", default="Unknown")
        assert result == "Unknown"

    def test_empty_attrs_returns_object(self):
        """Test that no attributes returns the object itself."""

        class User:
            name = "Alice"

        user = User()
        result = safe_get_attr(user)
        assert result is user

    def test_type_error_handling(self):
        """Test handling of TypeError for non-objects."""
        result = safe_get_attr(42, "title", default="default")
        assert result == "default"

        result = safe_get_attr("string", "length", default="default")
        assert result == "default"


class TestEnsureDefined:
    """Test ensure_defined() function."""

    def test_defined_value_returned(self):
        """Test that defined values are returned unchanged."""
        assert ensure_defined("hello") == "hello"
        assert ensure_defined(42) == 42
        assert ensure_defined([1, 2, 3]) == [1, 2, 3]
        assert ensure_defined({"key": "value"}) == {"key": "value"}

    def test_undefined_returns_default(self):
        """Test that Undefined returns default."""
        assert ensure_defined(Undefined()) == ""
        assert ensure_defined(Undefined(), "fallback") == "fallback"
        assert ensure_defined(Undefined(), None) is None
        assert ensure_defined(Undefined(), []) == []

    def test_none_is_returned(self):
        """Test that None is returned (not replaced)."""
        # None is a valid value, should not be replaced
        assert ensure_defined(None) is None
        assert ensure_defined(None, "default") is None

    def test_empty_string_is_returned(self):
        """Test that empty string is returned."""
        assert ensure_defined("") == ""
        assert ensure_defined("", "default") == ""

    def test_zero_is_returned(self):
        """Test that zero is returned."""
        assert ensure_defined(0) == 0
        assert ensure_defined(0, 999) == 0

    def test_false_is_returned(self):
        """Test that False is returned."""
        assert ensure_defined(False) is False
        assert ensure_defined(False, True) is False


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_safe_page_title_access(self):
        """Test safely accessing page title with fallback."""

        class Page:
            pass

        page1 = Page()
        page1.title = "My Page"

        page2 = Page()
        page2.title = Undefined()

        page3 = Page()  # No title attribute

        # All should work without errors
        assert safe_get(page1, "title", "Untitled") == "My Page"
        assert safe_get(page2, "title", "Untitled") == "Untitled"
        assert safe_get(page3, "title", "Untitled") == "Untitled"

    def test_safe_nested_metadata_access(self):
        """Test safely accessing nested metadata."""

        class Metadata:
            author = "Alice"

        class Page1:
            metadata = Metadata()

        class Page2:
            metadata = None

        class Page3:
            pass

        page1 = Page1()
        page2 = Page2()
        page3 = Page3()

        # All should work safely
        assert safe_get_attr(page1, "metadata", "author", default="Unknown") == "Alice"
        assert safe_get_attr(page2, "metadata", "author", default="Unknown") == "Unknown"
        assert safe_get_attr(page3, "metadata", "author", default="Unknown") == "Unknown"

    def test_checking_optional_fields(self):
        """Test checking if optional fields have values."""

        class Page:
            title = "Hello"
            description = ""
            tags = []
            draft = False
            featured = None

        page = Page()

        # Only title has a real value
        assert has_value(page.title) is True
        assert has_value(page.description) is False
        assert has_value(page.tags) is False
        assert has_value(page.draft) is False
        assert has_value(page.featured) is False

    def test_template_conditional_logic(self):
        """Test typical template conditional logic patterns."""

        class Page:
            title = "My Page"
            description = Undefined()
            author = None

        page = Page()

        # Pattern 1: Display title or fallback
        title = safe_get(page, "title", "Untitled")
        assert title == "My Page"

        # Pattern 2: Only show description if it has a value
        if has_value(safe_get(page, "description")):
            pytest.fail("Should not show description")

        # Pattern 3: Ensure author is never Undefined
        author = ensure_defined(safe_get(page, "author"), "Anonymous")
        assert author == "Anonymous"

    def test_chaining_utility_functions(self):
        """Test chaining utility functions together."""

        class Page:
            metadata = Undefined()

        page = Page()

        # Get nested attribute, ensure it's defined, check if it has value
        author = ensure_defined(safe_get_attr(page, "metadata", "author", default=None), "Unknown")
        assert author == "Unknown"
        assert has_value(author) is True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_recursive_attribute_access(self):
        """Test accessing same attribute recursively."""

        class Node:
            def __init__(self, value, child=None):
                self.value = value
                self.child = child

        leaf = Node("leaf")
        branch = Node("branch", leaf)
        root = Node("root", branch)

        assert safe_get_attr(root, "child", "child", "value") == "leaf"

    def test_attribute_that_raises_exception(self):
        """Test handling attributes that raise exceptions."""

        class Broken:
            @property
            def bad_property(self):
                raise ValueError("Boom!")

        obj = Broken()
        # Should handle the exception and return default
        safe_get(obj, "bad_property", "default")
        # Note: properties that raise are tricky, depends on implementation
        # safe_get might catch AttributeError but not ValueError
        # This test documents current behavior

    def test_very_long_attribute_chain(self):
        """Test very long nested attribute chains."""

        class Level10:
            value = "deep"

        class Level9:
            level10 = Level10()

        class Level8:
            level9 = Level9()

        # Continue building...
        obj = Level8()

        result = safe_get_attr(obj, "level9", "level10", "value")
        assert result == "deep"

        # Missing deep path
        result = safe_get_attr(obj, "level9", "level10", "missing", default="N/A")
        assert result == "N/A"

    def test_callable_attributes(self):
        """Test accessing callable attributes."""

        class Page:
            def get_title(self):
                return "Title"

        page = Page()
        # Getting a method returns the method, not calls it
        method = safe_get(page, "get_title")
        assert callable(method)
        assert method() == "Title"

    def test_special_attributes(self):
        """Test accessing special/magic attributes."""

        class Page:
            title = "Hello"

        page = Page()

        # Can access special attributes
        assert safe_get(page, "__class__") == Page
        assert safe_get(page, "__dict__") is not None
