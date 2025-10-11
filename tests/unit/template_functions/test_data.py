"""Tests for data manipulation template functions."""

import json
import tempfile
from pathlib import Path
from bengal.rendering.template_functions.data import (
    jsonify,
    merge,
    has_key,
    get_nested,
    keys_filter,
    values_filter,
    items_filter,
    get_data,
)


class TestJsonify:
    """Tests for jsonify filter."""
    
    def test_dict_to_json(self):
        data = {'name': 'Alice', 'age': 30}
        result = jsonify(data)
        assert json.loads(result) == data
    
    def test_list_to_json(self):
        data = [1, 2, 3]
        result = jsonify(data)
        assert json.loads(result) == data
    
    def test_with_indent(self):
        data = {'a': 1}
        result = jsonify(data, indent=2)
        assert '\n' in result  # Indented
    
    def test_invalid_data(self):
        # Objects can't be serialized
        result = jsonify(object())
        assert result == '{}'


class TestMerge:
    """Tests for merge filter."""
    
    def test_shallow_merge(self):
        dict1 = {'a': 1, 'b': 2}
        dict2 = {'b': 3, 'c': 4}
        result = merge(dict1, dict2, deep=False)
        assert result == {'a': 1, 'b': 3, 'c': 4}
    
    def test_deep_merge(self):
        dict1 = {'a': {'x': 1, 'y': 2}}
        dict2 = {'a': {'y': 3, 'z': 4}}
        result = merge(dict1, dict2, deep=True)
        assert result == {'a': {'x': 1, 'y': 3, 'z': 4}}
    
    def test_merge_non_dict(self):
        result = merge('not a dict', {'a': 1})
        assert result == {'a': 1}
    
    def test_empty_dicts(self):
        result = merge({}, {})
        assert result == {}


class TestHasKey:
    """Tests for has_key filter."""
    
    def test_key_exists(self):
        data = {'name': 'Alice', 'age': 30}
        assert has_key(data, 'name') is True
    
    def test_key_not_exists(self):
        data = {'name': 'Alice'}
        assert has_key(data, 'age') is False
    
    def test_non_dict(self):
        assert has_key('not a dict', 'key') is False
    
    def test_empty_dict(self):
        assert has_key({}, 'key') is False


class TestGetNested:
    """Tests for get_nested filter."""
    
    def test_simple_path(self):
        data = {'user': {'name': 'Alice'}}
        result = get_nested(data, 'user.name')
        assert result == 'Alice'
    
    def test_deep_path(self):
        data = {'user': {'profile': {'email': 'alice@example.com'}}}
        result = get_nested(data, 'user.profile.email')
        assert result == 'alice@example.com'
    
    def test_missing_path(self):
        data = {'user': {'name': 'Alice'}}
        result = get_nested(data, 'user.age', default='N/A')
        assert result == 'N/A'
    
    def test_non_dict(self):
        result = get_nested('not a dict', 'user.name')
        assert result is None
    
    def test_empty_path(self):
        data = {'a': 1}
        result = get_nested(data, '')
        assert result is None


class TestKeysFilter:
    """Tests for keys filter."""
    
    def test_get_keys(self):
        data = {'a': 1, 'b': 2, 'c': 3}
        result = keys_filter(data)
        assert set(result) == {'a', 'b', 'c'}
    
    def test_empty_dict(self):
        assert keys_filter({}) == []
    
    def test_non_dict(self):
        assert keys_filter('not a dict') == []


class TestValuesFilter:
    """Tests for values filter."""
    
    def test_get_values(self):
        data = {'a': 1, 'b': 2, 'c': 3}
        result = values_filter(data)
        assert set(result) == {1, 2, 3}
    
    def test_empty_dict(self):
        assert values_filter({}) == []
    
    def test_non_dict(self):
        assert values_filter('not a dict') == []


class TestItemsFilter:
    """Tests for items filter."""
    
    def test_get_items(self):
        data = {'a': 1, 'b': 2}
        result = items_filter(data)
        assert set(result) == {('a', 1), ('b', 2)}
    
    def test_empty_dict(self):
        assert items_filter({}) == []
    
    def test_non_dict(self):
        assert items_filter('not a dict') == []


class TestGetData:
    """Tests for get_data function."""
    
    def test_load_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a JSON file
            json_file = Path(tmpdir) / "data.json"
            data = {'name': 'Alice', 'age': 30}
            with open(json_file, 'w') as f:
                json.dump(data, f)
            
            result = get_data('data.json', Path(tmpdir))
            assert result == data
    
    def test_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_data('missing.json', Path(tmpdir))
            assert result == {}
    
    def test_empty_path(self):
        result = get_data('', Path('/tmp'))
        assert result == {}

