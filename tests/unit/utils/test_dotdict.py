"""Tests for DotDict utility."""

import pytest

from bengal.utils.primitives.dotdict import DotDict, wrap_data


class TestDotDictBasics:
    """Test basic DotDict functionality."""

    def test_dot_notation_access(self):
        """Test accessing values with dot notation."""
        data = DotDict({"name": "Alice", "age": 30})
        assert data.name == "Alice"
        assert data.age == 30

    def test_bracket_notation_access(self):
        """Test accessing values with bracket notation."""
        data = DotDict({"name": "Alice", "age": 30})
        assert data["name"] == "Alice"
        assert data["age"] == 30

    def test_missing_attribute_returns_empty_string(self):
        """Test that missing attributes return '' (consistent with ParamsContext)."""
        data = DotDict({"name": "Alice"})
        assert data.missing == ""
        assert data.nonexistent == ""

    def test_get_with_default(self):
        """Test get() method with default values."""
        data = DotDict({"name": "Alice"})
        assert data.get("name") == "Alice"
        assert (
            data.get("missing") is None
        )  # .get() returns None (not ''), consistent with dict.get()
        assert data.get("missing", "default") == "default"

    def test_contains(self):
        """Test 'in' operator."""
        data = DotDict({"name": "Alice", "age": 30})
        assert "name" in data
        assert "age" in data
        assert "missing" not in data

    def test_len(self):
        """Test len() function."""
        data = DotDict({"name": "Alice", "age": 30})
        assert len(data) == 2

        empty = DotDict()
        assert len(empty) == 0

    def test_iter(self):
        """Test iteration over keys."""
        data = DotDict({"name": "Alice", "age": 30})
        keys = list(data)
        assert set(keys) == {"name", "age"}

    def test_keys_values_items(self):
        """Test dict interface methods."""
        data = DotDict({"name": "Alice", "age": 30})

        assert set(data.keys()) == {"name", "age"}
        assert set(data.values()) == {"Alice", 30}
        assert set(data.items()) == {("name", "Alice"), ("age", 30)}

    def test_repr(self):
        """Test string representation."""
        data = DotDict({"name": "Alice"})
        assert repr(data) == "DotDict({'name': 'Alice'})"


class TestDotDictNested:
    """Test nested dictionary handling."""

    def test_nested_dict_wrapping(self):
        """Test that nested dicts are automatically wrapped."""
        data = DotDict({"user": {"name": "Bob", "age": 25}})
        assert isinstance(data.user, DotDict)
        assert data.user.name == "Bob"
        assert data.user.age == 25

    def test_deeply_nested_wrapping(self):
        """Test deeply nested dictionary wrapping."""
        data = DotDict({"level1": {"level2": {"level3": {"value": "deep"}}}})
        assert data.level1.level2.level3.value == "deep"

    def test_nested_caching(self):
        """Test that nested DotDict objects are cached."""
        data = DotDict({"user": {"name": "Bob"}})

        # First access creates wrapped object
        user1 = data.user
        # Second access should return same object (cached)
        user2 = data.user

        assert user1 is user2  # Same object reference

    def test_bracket_notation_nested(self):
        """Test bracket notation with nested dicts."""
        data = DotDict({"user": {"name": "Bob"}})
        assert isinstance(data["user"], DotDict)
        assert data["user"]["name"] == "Bob"

    def test_mixed_notation(self):
        """Test mixing dot and bracket notation."""
        data = DotDict({"user": {"profile": {"name": "Charlie"}}})
        assert data.user["profile"].name == "Charlie"
        assert data["user"].profile["name"] == "Charlie"


class TestDotDictMethodNameCollisions:
    """Test handling of method name collisions (the key feature)."""

    def test_items_field_not_method(self):
        """Test that 'items' field is accessible (not the method)."""
        # This is the core problem DotDict solves
        data = DotDict({"skills": {"category": "Programming", "items": ["Python", "JavaScript"]}})
        skills = data.skills

        # Should access the 'items' field, not the items() method
        assert skills.items == ["Python", "JavaScript"]
        assert isinstance(skills.items, list)

    def test_keys_field_not_method(self):
        """Test that 'keys' field is accessible."""
        data = DotDict({"metadata": {"keys": ["api_key", "secret_key"]}})
        assert data.metadata.keys == ["api_key", "secret_key"]

    def test_values_field_not_method(self):
        """Test that 'values' field is accessible."""
        data = DotDict({"config": {"values": [1, 2, 3]}})
        assert data.config.values == [1, 2, 3]

    def test_method_still_callable(self):
        """Test that methods are still accessible via the actual call."""
        data = DotDict({"name": "Alice", "items": ["a", "b"]})

        # Dot notation gets the field
        assert data.items == ["a", "b"]

        # But we can still call the method directly
        items_method = DotDict.items
        result = list(items_method(data))
        assert ("name", "Alice") in result


class TestDotDictModification:
    """Test modification operations."""

    def test_setattr_dot_notation(self):
        """Test setting values with dot notation."""
        data = DotDict()
        data.name = "Alice"
        data.age = 30
        assert data.name == "Alice"
        assert data.age == 30

    def test_setitem_bracket_notation(self):
        """Test setting values with bracket notation."""
        data = DotDict()
        data["name"] = "Alice"
        data["age"] = 30
        assert data["name"] == "Alice"
        assert data["age"] == 30

    def test_delattr(self):
        """Test deleting attributes."""
        data = DotDict({"name": "Alice", "age": 30})
        del data.age
        assert "age" not in data
        assert data.age == ""  # Returns '' for missing keys (consistent with ParamsContext)

    def test_delattr_nonexistent_raises(self):
        """Test deleting non-existent attribute raises error."""
        data = DotDict({"name": "Alice"})
        with pytest.raises(AttributeError):
            del data.nonexistent

    def test_delitem(self):
        """Test deleting items with bracket notation."""
        data = DotDict({"name": "Alice", "age": 30})
        del data["age"]
        assert "age" not in data

    def test_delitem_nonexistent_raises(self):
        """Test deleting non-existent item raises KeyError."""
        data = DotDict({"name": "Alice"})
        with pytest.raises(KeyError):
            del data["nonexistent"]

    def test_cache_invalidation_on_set(self):
        """Test that cache is invalidated when setting nested values."""
        data = DotDict({"user": {"name": "Alice"}})

        # Access to populate cache
        user1 = data.user
        assert user1.name == "Alice"

        # Modify the nested dict
        data.user = {"name": "Bob"}

        # Should get new object, not cached one
        user2 = data.user
        assert user2.name == "Bob"

    def test_cache_invalidation_on_del(self):
        """Test that cache is invalidated when deleting values."""
        data = DotDict({"user": {"name": "Alice"}})

        # Access to populate cache
        user1 = data.user
        assert user1.name == "Alice"

        # Delete and re-add
        del data.user
        data.user = {"name": "Charlie"}

        user2 = data.user
        assert user2.name == "Charlie"


class TestDotDictFromDict:
    """Test from_dict() recursive wrapping."""

    def test_from_dict_simple(self):
        """Test from_dict with simple dictionary."""
        source = {"name": "Alice", "age": 30}
        data = DotDict.from_dict(source)
        assert isinstance(data, DotDict)
        assert data.name == "Alice"
        assert data.age == 30

    def test_from_dict_nested(self):
        """Test from_dict recursively wraps nested dicts."""
        source = {"user": {"profile": {"name": "Bob"}}}
        data = DotDict.from_dict(source)

        assert isinstance(data, DotDict)
        assert isinstance(data.user, DotDict)
        assert isinstance(data.user.profile, DotDict)
        assert data.user.profile.name == "Bob"

    def test_from_dict_with_lists(self):
        """Test from_dict handles lists of dicts."""
        source = {
            "users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
        }
        data = DotDict.from_dict(source)

        assert isinstance(data, DotDict)
        assert isinstance(data.users, list)
        assert len(data.users) == 2

        # Dicts in lists should also be wrapped
        assert isinstance(data.users[0], DotDict)
        assert isinstance(data.users[1], DotDict)
        assert data.users[0].name == "Alice"
        assert data.users[1].name == "Bob"

    def test_from_dict_preserves_primitives(self):
        """Test from_dict preserves primitive types in lists."""
        source = {"numbers": [1, 2, 3], "strings": ["a", "b", "c"]}
        data = DotDict.from_dict(source)

        assert data.numbers == [1, 2, 3]
        assert data.strings == ["a", "b", "c"]


class TestWrapData:
    """Test wrap_data() helper function."""

    def test_wrap_dict(self):
        """Test wrapping a dictionary."""
        source = {"name": "Alice"}
        wrapped = wrap_data(source)
        assert isinstance(wrapped, DotDict)
        assert wrapped.name == "Alice"

    def test_wrap_nested_dict(self):
        """Test wrapping nested dictionaries."""
        source = {"user": {"name": "Bob"}}
        wrapped = wrap_data(source)
        assert isinstance(wrapped, DotDict)
        assert isinstance(wrapped.user, DotDict)
        assert wrapped.user.name == "Bob"

    def test_wrap_list_of_dicts(self):
        """Test wrapping list containing dicts."""
        source = [{"name": "Alice"}, {"name": "Bob"}]
        wrapped = wrap_data(source)

        assert isinstance(wrapped, list)
        assert isinstance(wrapped[0], DotDict)
        assert isinstance(wrapped[1], DotDict)
        assert wrapped[0].name == "Alice"
        assert wrapped[1].name == "Bob"

    def test_wrap_primitives(self):
        """Test wrapping primitives returns them unchanged."""
        assert wrap_data(42) == 42
        assert wrap_data("hello") == "hello"
        assert wrap_data(True) is True
        assert wrap_data(None) is None

    def test_wrap_mixed_structure(self):
        """Test wrapping complex mixed structures."""
        source = {
            "title": "Example",
            "metadata": {"author": "Alice", "tags": ["python", "testing"]},
            "items": [{"id": 1, "value": "first"}, {"id": 2, "value": "second"}],
            "count": 42,
        }
        wrapped = wrap_data(source)

        assert isinstance(wrapped, DotDict)
        assert wrapped.title == "Example"
        assert isinstance(wrapped.metadata, DotDict)
        assert wrapped.metadata.author == "Alice"
        assert wrapped.metadata.tags == ["python", "testing"]
        assert isinstance(wrapped.items[0], DotDict)
        assert wrapped.items[0].id == 1
        assert wrapped.count == 42


class TestDotDictToDict:
    """Test to_dict() conversion."""

    def test_to_dict_simple(self):
        """Test converting DotDict back to regular dict."""
        data = DotDict({"name": "Alice", "age": 30})
        result = data.to_dict()
        assert isinstance(result, dict)
        assert result == {"name": "Alice", "age": 30}

    def test_to_dict_nested(self):
        """Test to_dict with nested DotDict."""
        data = DotDict({"user": {"name": "Bob"}})
        result = data.to_dict()

        # Note: to_dict() only converts top level
        assert isinstance(result, dict)
        assert "user" in result


class TestDotDictEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_dotdict(self):
        """Test empty DotDict behaves correctly."""
        data = DotDict()
        assert len(data) == 0
        assert list(data) == []
        assert data.anything == ""  # Returns '' for missing keys

    def test_none_values(self):
        """Test DotDict with None values."""
        data = DotDict({"name": None, "age": 30})
        assert data.name is None
        assert data.age == 30

    def test_numeric_string_keys(self):
        """Test keys that look like numbers."""
        data = DotDict({"123": "numeric key", "normal": "value"})
        assert data["123"] == "numeric key"
        assert data.normal == "value"

    def test_special_characters_in_keys(self):
        """Test keys with special characters (only accessible via bracket notation)."""
        data = DotDict({"normal-key": "value1", "key.with.dots": "value2"})
        # Can only access special keys via brackets
        assert data["normal-key"] == "value1"
        assert data["key.with.dots"] == "value2"

    def test_underscore_keys(self):
        """Test keys with underscores."""
        data = DotDict({"first_name": "Alice", "last_name": "Smith"})
        assert data.first_name == "Alice"
        assert data.last_name == "Smith"

    def test_boolean_values(self):
        """Test boolean values are preserved."""
        data = DotDict({"active": True, "deleted": False})
        assert data.active is True
        assert data.deleted is False

    def test_list_values(self):
        """Test list values are preserved."""
        data = DotDict({"tags": ["python", "testing", "django"]})
        assert data.tags == ["python", "testing", "django"]
        assert isinstance(data.tags, list)

    def test_already_wrapped_dotdict(self):
        """Test that already-wrapped DotDict isn't double-wrapped."""
        inner = DotDict({"name": "Alice"})
        outer = DotDict({"user": inner})

        # Should preserve the DotDict, not wrap it again
        assert isinstance(outer.user, DotDict)
        assert outer.user.name == "Alice"


class TestDotDictJinja2Integration:
    """Test DotDict behavior in Jinja2-like scenarios."""

    def test_safe_conditionals(self):
        """Test that missing attributes work in conditionals."""
        data = DotDict({"name": "Alice"})

        # These should work without errors
        if data.missing:
            pytest.fail("Should not enter if block")

        if not data.missing:
            pass  # Should work

        if data.name:
            pass  # Should work
        else:
            pytest.fail("Should not enter else block")

    def test_method_collision_in_template_context(self):
        """Test the main use case: accessing 'items' field in templates."""
        # Simulating template data for resume/portfolio
        # Use from_dict to ensure nested dicts are also wrapped
        resume_data = DotDict.from_dict(
            {
                "skills": [
                    {"category": "Programming", "items": ["Python", "JavaScript", "Go"]},
                    {"category": "Databases", "items": ["PostgreSQL", "Redis"]},
                ]
            }
        )

        # This is what breaks with regular dicts in Jinja2:
        # {{ skill_group.items }} would call items() method, not get the field

        for skill_group in resume_data.skills:
            # Should get the field, not the method
            assert isinstance(skill_group.items, list)
            assert len(skill_group.items) > 0
            assert isinstance(skill_group.items[0], str)
