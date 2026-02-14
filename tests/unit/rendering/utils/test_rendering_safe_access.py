"""Tests for safe access utilities.

These tests verify the consolidated safe_access module which provides
safe attribute/dict access with Jinja2 Undefined handling.
"""

from __future__ import annotations

from jinja2 import Undefined

from bengal.rendering.utils.safe_access import (
    ensure_defined,
    has_value,
    is_undefined,
    safe_get,
    safe_get_nested,
)


class TestIsUndefined:
    """Tests for is_undefined function."""

    def test_undefined_object(self):
        """Undefined objects should return True."""
        assert is_undefined(Undefined()) is True

    def test_defined_values(self):
        """Defined values should return False."""
        assert is_undefined("hello") is False
        assert is_undefined(42) is False
        assert is_undefined([1, 2, 3]) is False
        assert is_undefined({"key": "value"}) is False

    def test_none_is_not_undefined(self):
        """None should not be considered Undefined."""
        assert is_undefined(None) is False

    def test_empty_string_is_not_undefined(self):
        """Empty string should not be Undefined."""
        assert is_undefined("") is False

    def test_zero_is_not_undefined(self):
        """Zero should not be Undefined."""
        assert is_undefined(0) is False


class TestSafeGet:
    """Tests for safe_get function."""

    def test_get_from_object_attribute(self):
        """Should get attribute from object."""

        class Page:
            title = "Hello World"

        page = Page()
        assert safe_get(page, "title") == "Hello World"

    def test_get_from_dict(self):
        """Should get key from dict."""
        data = {"title": "Test", "count": 42}
        assert safe_get(data, "title") == "Test"
        assert safe_get(data, "count") == 42

    def test_missing_attribute_returns_default(self):
        """Missing attribute should return default."""

        class Page:
            title = "Hello"

        page = Page()
        assert safe_get(page, "missing") is None
        assert safe_get(page, "missing", "default") == "default"

    def test_missing_dict_key_returns_default(self):
        """Missing dict key should return default."""
        data = {"title": "Test"}
        assert safe_get(data, "missing") is None
        assert safe_get(data, "missing", "default") == "default"

    def test_undefined_value_returns_default(self):
        """Undefined attribute value should return default."""

        class Page:
            title = Undefined()

        page = Page()
        assert safe_get(page, "title", "Untitled") == "Untitled"

    def test_none_value_returns_none(self):
        """Explicitly set None should be returned (not replaced with default)."""

        class Page:
            title = None

        page = Page()
        result = safe_get(page, "title", "default")
        assert result is None

    def test_primitives_return_default(self):
        """Primitives should return default (no attribute access)."""
        assert safe_get(42, "anything", "default") == "default"
        assert safe_get("string", "anything", "default") == "default"
        assert safe_get(True, "anything", "default") == "default"

    def test_undefined_object_returns_default(self):
        """Undefined object itself should return default."""
        assert safe_get(Undefined(), "anything", "default") == "default"


class TestSafeGetNested:
    """Tests for safe_get_nested function."""

    def test_single_level_access(self):
        """Should work for single-level access."""

        class Page:
            title = "Hello"

        page = Page()
        assert safe_get_nested(page, "title") == "Hello"

    def test_nested_access(self):
        """Should traverse nested attributes."""

        class Profile:
            name = "Alice"

        class User:
            profile = Profile()

        user = User()
        assert safe_get_nested(user, "profile", "name") == "Alice"

    def test_deeply_nested_access(self):
        """Should work with deeply nested attributes."""

        class Address:
            city = "Seattle"

        class Profile:
            address = Address()

        class User:
            profile = Profile()

        user = User()
        assert safe_get_nested(user, "profile", "address", "city") == "Seattle"

    def test_nested_dict_access(self):
        """Should traverse nested dicts."""
        data = {"config": {"theme": {"color": "blue"}}}
        assert safe_get_nested(data, "config", "theme", "color") == "blue"

    def test_missing_intermediate_returns_default(self):
        """Missing intermediate attribute should return default."""

        class User:
            name = "Alice"

        user = User()
        result = safe_get_nested(user, "profile", "name", default="Unknown")
        assert result == "Unknown"

    def test_missing_final_returns_default(self):
        """Missing final attribute should return default."""

        class Profile:
            name = "Alice"

        class User:
            profile = Profile()

        user = User()
        result = safe_get_nested(user, "profile", "missing", default="N/A")
        assert result == "N/A"

    def test_undefined_intermediate_returns_default(self):
        """Undefined intermediate should return default."""

        class User:
            profile = Undefined()

        user = User()
        result = safe_get_nested(user, "profile", "name", default="Unknown")
        assert result == "Unknown"

    def test_none_intermediate_returns_default(self):
        """None intermediate should return default."""

        class User:
            profile = None

        user = User()
        result = safe_get_nested(user, "profile", "name", default="Unknown")
        assert result == "Unknown"

    def test_empty_attrs_returns_object(self):
        """No attributes should return the object itself."""

        class User:
            name = "Alice"

        user = User()
        result = safe_get_nested(user)
        assert result is user


class TestHasValue:
    """Tests for has_value function."""

    def test_truthy_values(self):
        """Truthy values should return True."""
        assert has_value("hello") is True
        assert has_value(42) is True
        assert has_value([1, 2, 3]) is True
        assert has_value({"key": "value"}) is True
        assert has_value(True) is True

    def test_falsy_values(self):
        """Falsy values should return False."""
        assert has_value("") is False
        assert has_value(0) is False
        assert has_value([]) is False
        assert has_value({}) is False
        assert has_value(False) is False
        assert has_value(None) is False

    def test_undefined_returns_false(self):
        """Undefined should return False."""
        assert has_value(Undefined()) is False


class TestEnsureDefined:
    """Tests for ensure_defined function."""

    def test_defined_value_returned(self):
        """Defined values should be returned unchanged."""
        assert ensure_defined("hello") == "hello"
        assert ensure_defined(42) == 42
        assert ensure_defined([1, 2, 3]) == [1, 2, 3]

    def test_undefined_returns_default(self):
        """Undefined should return default."""
        assert ensure_defined(Undefined()) == ""
        assert ensure_defined(Undefined(), "fallback") == "fallback"

    def test_none_is_replaced(self):
        """None should be replaced with default."""
        assert ensure_defined(None) == ""
        assert ensure_defined(None, "default") == "default"

    def test_empty_string_is_returned(self):
        """Empty string is a valid value and should be returned."""
        assert ensure_defined("") == ""
        assert ensure_defined("", "default") == ""

    def test_zero_is_returned(self):
        """Zero is a valid value and should be returned."""
        assert ensure_defined(0) == 0
        assert ensure_defined(0, 999) == 0

    def test_false_is_returned(self):
        """False is a valid value and should be returned."""
        assert ensure_defined(False) is False
        assert ensure_defined(False, True) is False
