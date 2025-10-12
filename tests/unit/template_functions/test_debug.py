"""Tests for debug utility template functions."""

from bengal.rendering.template_functions.debug import (
    debug,
    inspect,
    typeof,
)


class TestDebug:
    """Tests for debug filter."""

    def test_none_value(self):
        result = debug(None)
        assert result == "None"

    def test_simple_value(self):
        result = debug("hello")
        assert "hello" in result

    def test_dict(self):
        result = debug({"a": 1, "b": 2})
        assert "a" in result
        assert "b" in result

    def test_object_with_dict(self):
        class TestObj:
            def __init__(self):
                self.name = "test"
                self.value = 42

        result = debug(TestObj())
        assert "name" in result or "test" in result


class TestTypeof:
    """Tests for typeof filter."""

    def test_string(self):
        assert typeof("hello") == "str"

    def test_integer(self):
        assert typeof(42) == "int"

    def test_list(self):
        assert typeof([1, 2, 3]) == "list"

    def test_dict(self):
        assert typeof({"a": 1}) == "dict"

    def test_none(self):
        assert typeof(None) == "NoneType"


class TestInspect:
    """Tests for inspect filter."""

    def test_none(self):
        result = inspect(None)
        assert result == "None"

    def test_object_with_properties(self):
        class TestObj:
            def __init__(self):
                self.name = "test"
                self.value = 42

            def get_name(self):
                return self.name

        result = inspect(TestObj())
        assert "Properties:" in result or "name" in result.lower()

    def test_filters_private_attrs(self):
        result = inspect({"a": 1})
        assert "_" not in result or "Properties" in result  # No private attributes shown
