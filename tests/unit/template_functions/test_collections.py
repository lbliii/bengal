"""Tests for collection template functions."""

import pytest
from bengal.rendering.template_functions.collections import (
    where,
    where_not,
    group_by,
    sort_by,
    limit,
    offset,
    uniq,
    flatten,
)


class TestWhere:
    """Tests for where filter."""
    
    def test_filter_dicts(self):
        items = [
            {'name': 'Alice', 'age': 30},
            {'name': 'Bob', 'age': 25},
            {'name': 'Charlie', 'age': 30},
        ]
        result = where(items, 'age', 30)
        assert len(result) == 2
        assert result[0]['name'] == 'Alice'
        assert result[1]['name'] == 'Charlie'
    
    def test_filter_objects(self):
        class Person:
            def __init__(self, name, age):
                self.name = name
                self.age = age
        
        items = [
            Person('Alice', 30),
            Person('Bob', 25),
            Person('Charlie', 30),
        ]
        result = where(items, 'age', 30)
        assert len(result) == 2
        assert result[0].name == 'Alice'
    
    def test_no_matches(self):
        items = [{'type': 'a'}, {'type': 'b'}]
        result = where(items, 'type', 'c')
        assert result == []
    
    def test_empty_list(self):
        assert where([], 'key', 'value') == []
    
    def test_missing_key(self):
        items = [{'name': 'Alice'}, {'name': 'Bob'}]
        result = where(items, 'age', 30)
        assert result == []


class TestWhereNot:
    """Tests for where_not filter."""
    
    def test_filter_dicts(self):
        items = [
            {'status': 'active'},
            {'status': 'archived'},
            {'status': 'active'},
        ]
        result = where_not(items, 'status', 'archived')
        assert len(result) == 2
        assert all(item['status'] == 'active' for item in result)
    
    def test_empty_list(self):
        assert where_not([], 'key', 'value') == []


class TestGroupBy:
    """Tests for group_by filter."""
    
    def test_group_dicts(self):
        items = [
            {'category': 'fruit', 'name': 'apple'},
            {'category': 'vegetable', 'name': 'carrot'},
            {'category': 'fruit', 'name': 'banana'},
        ]
        result = group_by(items, 'category')
        assert len(result) == 2
        assert len(result['fruit']) == 2
        assert len(result['vegetable']) == 1
    
    def test_group_objects(self):
        class Item:
            def __init__(self, category, name):
                self.category = category
                self.name = name
        
        items = [
            Item('A', 'item1'),
            Item('B', 'item2'),
            Item('A', 'item3'),
        ]
        result = group_by(items, 'category')
        assert len(result) == 2
        assert len(result['A']) == 2
    
    def test_empty_list(self):
        assert group_by([], 'key') == {}


class TestSortBy:
    """Tests for sort_by filter."""
    
    def test_sort_dicts_asc(self):
        items = [
            {'age': 30},
            {'age': 25},
            {'age': 35},
        ]
        result = sort_by(items, 'age')
        assert result[0]['age'] == 25
        assert result[2]['age'] == 35
    
    def test_sort_dicts_desc(self):
        items = [
            {'age': 30},
            {'age': 25},
            {'age': 35},
        ]
        result = sort_by(items, 'age', reverse=True)
        assert result[0]['age'] == 35
        assert result[2]['age'] == 25
    
    def test_sort_objects(self):
        class Item:
            def __init__(self, value):
                self.value = value
        
        items = [Item(3), Item(1), Item(2)]
        result = sort_by(items, 'value')
        assert result[0].value == 1
    
    def test_empty_list(self):
        assert sort_by([], 'key') == []
    
    def test_missing_key(self):
        items = [{'a': 1}, {'b': 2}]
        # Should handle gracefully
        result = sort_by(items, 'c')
        assert len(result) == 2


class TestLimit:
    """Tests for limit filter."""
    
    def test_limit_less_than_length(self):
        items = [1, 2, 3, 4, 5]
        result = limit(items, 3)
        assert result == [1, 2, 3]
    
    def test_limit_more_than_length(self):
        items = [1, 2, 3]
        result = limit(items, 10)
        assert result == [1, 2, 3]
    
    def test_limit_zero(self):
        items = [1, 2, 3]
        result = limit(items, 0)
        assert result == []
    
    def test_empty_list(self):
        assert limit([], 5) == []


class TestOffset:
    """Tests for offset filter."""
    
    def test_offset_middle(self):
        items = [1, 2, 3, 4, 5]
        result = offset(items, 2)
        assert result == [3, 4, 5]
    
    def test_offset_all(self):
        items = [1, 2, 3]
        result = offset(items, 10)
        assert result == []
    
    def test_offset_zero(self):
        items = [1, 2, 3]
        result = offset(items, 0)
        assert result == [1, 2, 3]
    
    def test_empty_list(self):
        assert offset([], 5) == []


class TestUniq:
    """Tests for uniq filter."""
    
    def test_remove_duplicates(self):
        items = [1, 2, 2, 3, 1, 4]
        result = uniq(items)
        assert result == [1, 2, 3, 4]
    
    def test_preserve_order(self):
        items = [3, 1, 2, 1, 3]
        result = uniq(items)
        assert result == [3, 1, 2]
    
    def test_no_duplicates(self):
        items = [1, 2, 3]
        result = uniq(items)
        assert result == [1, 2, 3]
    
    def test_empty_list(self):
        assert uniq([]) == []
    
    def test_unhashable_types(self):
        items = [{'a': 1}, {'b': 2}, {'a': 1}]
        result = uniq(items)
        assert len(result) == 2  # Correctly removes duplicate dict


class TestFlatten:
    """Tests for flatten filter."""
    
    def test_flatten_nested_lists(self):
        items = [[1, 2], [3, 4], [5]]
        result = flatten(items)
        assert result == [1, 2, 3, 4, 5]
    
    def test_flatten_mixed(self):
        items = [[1, 2], 3, [4, 5]]
        result = flatten(items)
        assert result == [1, 2, 3, 4, 5]
    
    def test_flatten_empty_lists(self):
        items = [[1], [], [2]]
        result = flatten(items)
        assert result == [1, 2]
    
    def test_flatten_tuples(self):
        items = [(1, 2), (3, 4)]
        result = flatten(items)
        assert result == [1, 2, 3, 4]
    
    def test_empty_list(self):
        assert flatten([]) == []

