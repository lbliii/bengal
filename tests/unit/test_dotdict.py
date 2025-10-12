"""Tests for DotDict with caching optimization."""

import pytest

from bengal.utils.dotdict import DotDict, wrap_data


class TestDotDictBasicAccess:
    """Test basic DotDict functionality."""

    def test_dot_notation_access(self):
        """Test accessing values via dot notation."""
        data = DotDict({"name": "Alice", "age": 30})
        assert data.name == "Alice"
        assert data.age == 30

    def test_bracket_notation_access(self):
        """Test accessing values via bracket notation."""
        data = DotDict({"name": "Alice", "age": 30})
        assert data["name"] == "Alice"
        assert data["age"] == 30

    def test_nested_dict_access(self):
        """Test accessing nested dictionaries."""
        data = DotDict({"user": {"name": "Bob", "profile": {"bio": "Developer"}}})
        assert data.user.name == "Bob"
        assert data.user.profile.bio == "Developer"

    def test_list_access(self):
        """Test accessing lists."""
        data = DotDict({"items": ["a", "b", "c"]})
        assert data.items == ["a", "b", "c"]

    def test_none_for_missing_keys(self):
        """Test that missing keys return None (for Jinja2 compatibility)."""
        data = DotDict({"name": "Alice"})
        assert data.nonexistent is None

    def test_dict_methods_preserved(self):
        """Test that dict methods still work."""
        data = DotDict({"name": "Alice", "age": 30})
        assert "name" in data
        assert 30 in data.values()
        assert ("name", "Alice") in data.items()


class TestDotDictCaching:
    """Test that caching works correctly and improves performance."""

    def test_nested_dict_returns_same_object(self):
        """Test that accessing nested dict multiple times returns same cached object."""
        data = DotDict({"user": {"name": "Bob"}})

        # First access
        user1 = data.user
        # Second access
        user2 = data.user

        # Should be the exact same object (cached)
        assert user1 is user2

    def test_deeply_nested_caching(self):
        """Test caching with deeply nested structures."""
        data = DotDict({"level1": {"level2": {"level3": {"value": "deep"}}}})

        # Should cache intermediate levels
        level1_first = data.level1
        level1_second = data.level1
        assert level1_first is level1_second

        level2_first = data.level1.level2
        level2_second = data.level1.level2
        assert level2_first is level2_second

    def test_bracket_notation_caching(self):
        """Test that bracket notation also uses cache."""
        data = DotDict({"user": {"name": "Bob"}})

        user1 = data["user"]
        user2 = data["user"]

        assert user1 is user2

    def test_mixed_access_caching(self):
        """Test that dot and bracket notation share cache."""
        data = DotDict({"user": {"name": "Bob"}})

        user_dot = data.user
        user_bracket = data["user"]

        # Should be the same cached object
        assert user_dot is user_bracket


class TestDotDictCacheInvalidation:
    """Test that cache is properly invalidated on mutations."""

    def test_setattr_invalidates_cache(self):
        """Test that setting a value invalidates the cache."""
        data = DotDict({"user": {"name": "Bob"}})

        # Access and cache
        user1 = data.user
        assert user1.name == "Bob"

        # Update the value
        data.user = {"name": "Alice"}

        # Should return new wrapped object
        user2 = data.user
        assert user2.name == "Alice"
        assert user1 is not user2

    def test_setitem_invalidates_cache(self):
        """Test that bracket notation assignment invalidates cache."""
        data = DotDict({"user": {"name": "Bob"}})

        user1 = data["user"]
        assert user1.name == "Bob"

        # Update via bracket notation
        data["user"] = {"name": "Alice"}

        user2 = data["user"]
        assert user2.name == "Alice"
        assert user1 is not user2

    def test_delattr_invalidates_cache(self):
        """Test that deleting a value invalidates the cache."""
        data = DotDict({"user": {"name": "Bob"}, "admin": {"name": "Admin"}})

        # Access and cache
        _ = data.user

        # Delete
        del data.user

        # Should not exist anymore
        assert data.user is None

    def test_delitem_invalidates_cache(self):
        """Test that bracket notation deletion invalidates cache."""
        data = DotDict({"user": {"name": "Bob"}, "admin": {"name": "Admin"}})

        # Access and cache
        _ = data["user"]

        # Delete via bracket notation
        del data["user"]

        # Should not exist anymore
        assert "user" not in data


class TestDotDictMutations:
    """Test DotDict modification operations."""

    def test_setattr_new_key(self):
        """Test adding new keys via dot notation."""
        data = DotDict({"name": "Alice"})
        data.age = 30
        assert data.age == 30

    def test_setitem_new_key(self):
        """Test adding new keys via bracket notation."""
        data = DotDict({"name": "Alice"})
        data["age"] = 30
        assert data["age"] == 30

    def test_nested_modification(self):
        """Test modifying nested structures."""
        data = DotDict({"user": {"name": "Bob"}})
        data.user.age = 25
        assert data.user.age == 25

    def test_delattr_existing_key(self):
        """Test deleting existing keys via dot notation."""
        data = DotDict({"name": "Alice", "age": 30})
        del data.age
        assert "age" not in data

    def test_delattr_missing_key(self):
        """Test deleting non-existent key raises AttributeError."""
        data = DotDict({"name": "Alice"})
        with pytest.raises(AttributeError):
            del data.nonexistent

    def test_delitem_existing_key(self):
        """Test deleting existing keys via bracket notation."""
        data = DotDict({"name": "Alice", "age": 30})
        del data["age"]
        assert "age" not in data


class TestDotDictDictInterface:
    """Test dict-like interface methods."""

    def test_len(self):
        """Test len() function."""
        data = DotDict({"a": 1, "b": 2, "c": 3})
        assert len(data) == 3

    def test_contains(self):
        """Test 'in' operator."""
        data = DotDict({"name": "Alice", "age": 30})
        assert "name" in data
        assert "nonexistent" not in data

    def test_iter(self):
        """Test iteration over keys."""
        data = DotDict({"a": 1, "b": 2, "c": 3})
        keys = list(data)
        assert set(keys) == {"a", "b", "c"}

    def test_get_with_default(self):
        """Test get() method with default value."""
        data = DotDict({"name": "Alice"})
        assert data.get("name") == "Alice"
        assert data.get("age", 30) == 30
        assert data.get("nonexistent") is None

    def test_keys(self):
        """Test keys() method."""
        data = DotDict({"a": 1, "b": 2})
        assert set(data.keys()) == {"a", "b"}

    def test_values(self):
        """Test values() method."""
        data = DotDict({"a": 1, "b": 2})
        assert set(data.values()) == {1, 2}

    def test_items(self):
        """Test items() method."""
        data = DotDict({"a": 1, "b": 2})
        assert set(data.items()) == {("a", 1), ("b", 2)}


class TestDotDictFromDict:
    """Test DotDict.from_dict() class method."""

    def test_simple_dict(self):
        """Test creating DotDict from simple dict."""
        source = {"name": "Alice", "age": 30}
        data = DotDict.from_dict(source)
        assert data.name == "Alice"
        assert data.age == 30

    def test_nested_dict(self):
        """Test from_dict with nested dicts."""
        source = {"user": {"name": "Bob", "profile": {"bio": "Developer"}}}
        data = DotDict.from_dict(source)
        assert data.user.name == "Bob"
        assert data.user.profile.bio == "Developer"

    def test_list_with_dicts(self):
        """Test from_dict with lists containing dicts."""
        source = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}
        data = DotDict.from_dict(source)
        assert data.users[0].name == "Alice"
        assert data.users[1].name == "Bob"

    def test_mixed_structure(self):
        """Test from_dict with complex nested structure."""
        source = {
            "team": {
                "name": "Engineering",
                "members": [
                    {"name": "Alice", "skills": {"items": ["Python", "Go"]}},
                    {"name": "Bob", "skills": {"items": ["JavaScript"]}},
                ],
            }
        }
        data = DotDict.from_dict(source)
        assert data.team.name == "Engineering"
        assert data.team.members[0].name == "Alice"
        assert data.team.members[0].skills.items == ["Python", "Go"]


class TestDotDictToDict:
    """Test DotDict.to_dict() method."""

    def test_simple_to_dict(self):
        """Test converting simple DotDict to dict."""
        data = DotDict({"name": "Alice", "age": 30})
        result = data.to_dict()
        assert result == {"name": "Alice", "age": 30}
        assert isinstance(result, dict)

    def test_nested_to_dict(self):
        """Test to_dict returns underlying nested structure."""
        data = DotDict({"user": {"name": "Bob"}})
        result = data.to_dict()
        assert result == {"user": {"name": "Bob"}}


class TestWrapData:
    """Test wrap_data() helper function."""

    def test_wrap_dict(self):
        """Test wrapping a dict."""
        data = {"name": "Alice", "age": 30}
        wrapped = wrap_data(data)
        assert isinstance(wrapped, DotDict)
        assert wrapped.name == "Alice"

    def test_wrap_nested_dict(self):
        """Test wrapping nested dicts."""
        data = {"user": {"name": "Bob"}}
        wrapped = wrap_data(data)
        assert isinstance(wrapped, DotDict)
        assert wrapped.user.name == "Bob"

    def test_wrap_list(self):
        """Test wrapping lists."""
        data = [1, 2, 3]
        wrapped = wrap_data(data)
        assert wrapped == [1, 2, 3]

    def test_wrap_list_with_dicts(self):
        """Test wrapping lists containing dicts."""
        data = [{"name": "Alice"}, {"name": "Bob"}]
        wrapped = wrap_data(data)
        assert isinstance(wrapped[0], DotDict)
        assert wrapped[0].name == "Alice"

    def test_wrap_primitives(self):
        """Test wrapping primitive values."""
        assert wrap_data(42) == 42
        assert wrap_data("hello") == "hello"
        assert wrap_data(None) is None


class TestDotDictJinja2Compatibility:
    """Test features specifically for Jinja2 template compatibility."""

    def test_field_named_items(self):
        """Test accessing a field named 'items' (not the method)."""
        data = DotDict({"category": "Programming", "items": ["Python", "Go"]})
        # Should access the field, not the items() method
        assert data.items == ["Python", "Go"]

    def test_field_named_keys(self):
        """Test accessing a field named 'keys'."""
        data = DotDict({"title": "Config", "keys": ["api_key", "secret"]})
        assert data.keys == ["api_key", "secret"]

    def test_field_named_values(self):
        """Test accessing a field named 'values'."""
        data = DotDict({"config": "Settings", "values": [1, 2, 3]})
        assert data.values == [1, 2, 3]

    def test_safe_conditionals(self):
        """Test that missing fields return None for safe conditionals."""
        data = DotDict({"name": "Alice"})
        # In Jinja2: {% if obj.field %} won't raise error
        assert data.nonexistent is None
        assert not data.nonexistent


class TestDotDictRepr:
    """Test string representation."""

    def test_repr_simple(self):
        """Test repr for simple DotDict."""
        data = DotDict({"name": "Alice"})
        assert repr(data) == "DotDict({'name': 'Alice'})"

    def test_repr_nested(self):
        """Test repr for nested DotDict."""
        data = DotDict({"user": {"name": "Bob"}})
        assert "DotDict" in repr(data)
        assert "user" in repr(data)


class TestDotDictPerformance:
    """Test performance characteristics of caching."""

    def test_no_repeated_wrapping(self):
        """Test that nested dicts are not repeatedly wrapped."""
        data = DotDict({"level1": {"level2": {"level3": {"value": "test"}}}})

        # Access nested structure multiple times
        for _ in range(100):
            _ = data.level1.level2.level3.value

        # The cache should have stored intermediate wrappers
        # We verify this by checking object identity
        level1_a = data.level1
        level1_b = data.level1
        assert level1_a is level1_b

        level2_a = data.level1.level2
        level2_b = data.level1.level2
        assert level2_a is level2_b

    def test_list_items_not_cached(self):
        """Test that list items are not cached (expected behavior)."""
        data = DotDict({"users": [{"name": "Alice"}, {"name": "Bob"}]})

        # List items should be wrapped but not cached at DotDict level
        # (the list is stored as-is, wrapping happens in from_dict)
        users = data.users
        assert isinstance(users, list)
