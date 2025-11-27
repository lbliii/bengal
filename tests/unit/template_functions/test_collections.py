"""Tests for collection template functions."""

from bengal.rendering.template_functions.collections import (
    complement,
    first,
    flatten,
    group_by,
    intersect,
    last,
    limit,
    offset,
    reverse,
    sort_by,
    uniq,
    union,
    where,
    where_not,
)


class TestWhere:
    """Tests for where filter."""

    def test_filter_dicts(self):
        items = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
            {"name": "Charlie", "age": 30},
        ]
        result = where(items, "age", 30)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Charlie"

    def test_filter_objects(self):
        class Person:
            def __init__(self, name, age):
                self.name = name
                self.age = age

        items = [
            Person("Alice", 30),
            Person("Bob", 25),
            Person("Charlie", 30),
        ]
        result = where(items, "age", 30)
        assert len(result) == 2
        assert result[0].name == "Alice"

    def test_no_matches(self):
        items = [{"type": "a"}, {"type": "b"}]
        result = where(items, "type", "c")
        assert result == []

    def test_empty_list(self):
        assert where([], "key", "value") == []

    def test_missing_key(self):
        items = [{"name": "Alice"}, {"name": "Bob"}]
        result = where(items, "age", 30)
        assert result == []


class TestWhereNot:
    """Tests for where_not filter."""

    def test_filter_dicts(self):
        items = [
            {"status": "active"},
            {"status": "archived"},
            {"status": "active"},
        ]
        result = where_not(items, "status", "archived")
        assert len(result) == 2
        assert all(item["status"] == "active" for item in result)

    def test_empty_list(self):
        assert where_not([], "key", "value") == []


class TestGroupBy:
    """Tests for group_by filter."""

    def test_group_dicts(self):
        items = [
            {"category": "fruit", "name": "apple"},
            {"category": "vegetable", "name": "carrot"},
            {"category": "fruit", "name": "banana"},
        ]
        result = group_by(items, "category")
        assert len(result) == 2
        assert len(result["fruit"]) == 2
        assert len(result["vegetable"]) == 1

    def test_group_objects(self):
        class Item:
            def __init__(self, category, name):
                self.category = category
                self.name = name

        items = [
            Item("A", "item1"),
            Item("B", "item2"),
            Item("A", "item3"),
        ]
        result = group_by(items, "category")
        assert len(result) == 2
        assert len(result["A"]) == 2

    def test_empty_list(self):
        assert group_by([], "key") == {}


class TestSortBy:
    """Tests for sort_by filter."""

    def test_sort_dicts_asc(self):
        items = [
            {"age": 30},
            {"age": 25},
            {"age": 35},
        ]
        result = sort_by(items, "age")
        assert result[0]["age"] == 25
        assert result[2]["age"] == 35

    def test_sort_dicts_desc(self):
        items = [
            {"age": 30},
            {"age": 25},
            {"age": 35},
        ]
        result = sort_by(items, "age", reverse=True)
        assert result[0]["age"] == 35
        assert result[2]["age"] == 25

    def test_sort_objects(self):
        class Item:
            def __init__(self, value):
                self.value = value

        items = [Item(3), Item(1), Item(2)]
        result = sort_by(items, "value")
        assert result[0].value == 1

    def test_empty_list(self):
        assert sort_by([], "key") == []

    def test_missing_key(self):
        items = [{"a": 1}, {"b": 2}]
        # Should handle gracefully
        result = sort_by(items, "c")
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
        items = [{"a": 1}, {"b": 2}, {"a": 1}]
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


class TestFirst:
    """Tests for first filter (Hugo-like)."""

    def test_first_returns_first_item(self):
        items = [1, 2, 3]
        assert first(items) == 1

    def test_first_with_dicts(self):
        items = [{"name": "Alice"}, {"name": "Bob"}]
        assert first(items) == {"name": "Alice"}

    def test_first_single_item(self):
        assert first([42]) == 42

    def test_first_empty_returns_none(self):
        assert first([]) is None

    def test_first_with_none_values(self):
        items = [None, 1, 2]
        assert first(items) is None  # Returns first item even if None


class TestLast:
    """Tests for last filter (Hugo-like)."""

    def test_last_returns_last_item(self):
        items = [1, 2, 3]
        assert last(items) == 3

    def test_last_with_dicts(self):
        items = [{"name": "Alice"}, {"name": "Bob"}]
        assert last(items) == {"name": "Bob"}

    def test_last_single_item(self):
        assert last([42]) == 42

    def test_last_empty_returns_none(self):
        assert last([]) is None

    def test_last_with_none_values(self):
        items = [1, 2, None]
        assert last(items) is None  # Returns last item even if None


class TestReverse:
    """Tests for reverse filter (Hugo-like)."""

    def test_reverse_list(self):
        items = [1, 2, 3]
        assert reverse(items) == [3, 2, 1]

    def test_reverse_preserves_original(self):
        items = [1, 2, 3]
        result = reverse(items)
        assert items == [1, 2, 3]  # Original unchanged
        assert result == [3, 2, 1]

    def test_reverse_single_item(self):
        assert reverse([42]) == [42]

    def test_reverse_empty(self):
        assert reverse([]) == []

    def test_reverse_with_dicts(self):
        items = [{"a": 1}, {"b": 2}, {"c": 3}]
        result = reverse(items)
        assert result[0] == {"c": 3}
        assert result[2] == {"a": 1}


class TestUnion:
    """Tests for union filter (set operations)."""

    def test_union_combines_lists(self):
        result = union([1, 2], [2, 3])
        assert result == [1, 2, 3]

    def test_union_preserves_order_from_first(self):
        result = union([3, 1], [2, 1])
        assert result == [3, 1, 2]

    def test_union_empty_first(self):
        result = union([], [1, 2])
        assert result == [1, 2]

    def test_union_empty_second(self):
        result = union([1, 2], [])
        assert result == [1, 2]

    def test_union_both_empty(self):
        assert union([], []) == []

    def test_union_no_duplicates_in_first(self):
        result = union([1, 1, 2], [3])
        assert result == [1, 2, 3]

    def test_union_with_dicts(self):
        # Dicts use string representation for uniqueness
        items1 = [{"a": 1}]
        items2 = [{"b": 2}]
        result = union(items1, items2)
        assert len(result) == 2


class TestIntersect:
    """Tests for intersect filter (set operations)."""

    def test_intersect_common_items(self):
        result = intersect([1, 2, 3], [2, 3, 4])
        assert result == [2, 3]

    def test_intersect_no_common(self):
        result = intersect([1, 2], [3, 4])
        assert result == []

    def test_intersect_all_common(self):
        result = intersect([1, 2], [1, 2])
        assert result == [1, 2]

    def test_intersect_empty_first(self):
        assert intersect([], [1, 2]) == []

    def test_intersect_empty_second(self):
        assert intersect([1, 2], []) == []

    def test_intersect_preserves_order_from_first(self):
        result = intersect([3, 1, 2], [2, 1])
        assert result == [1, 2]

    def test_intersect_removes_duplicates(self):
        result = intersect([1, 1, 2, 2], [1, 2])
        assert result == [1, 2]


class TestComplement:
    """Tests for complement filter (set difference)."""

    def test_complement_removes_second(self):
        result = complement([1, 2, 3], [2])
        assert result == [1, 3]

    def test_complement_empty_second(self):
        result = complement([1, 2], [])
        assert result == [1, 2]

    def test_complement_empty_first(self):
        assert complement([], [1, 2]) == []

    def test_complement_all_removed(self):
        result = complement([1, 2], [1, 2, 3])
        assert result == []

    def test_complement_none_removed(self):
        result = complement([1, 2], [3, 4])
        assert result == [1, 2]

    def test_complement_preserves_order(self):
        result = complement([3, 1, 2], [1])
        assert result == [3, 2]

    def test_complement_removes_duplicates(self):
        result = complement([1, 1, 2, 2], [1])
        assert result == [2]


class TestWhereOperators:
    """Tests for Hugo-like operators in where filter."""

    def test_where_eq_operator_default(self):
        """Test that 'eq' is the default operator."""
        items = [{"age": 20}, {"age": 30}, {"age": 40}]
        result = where(items, "age", 30)
        assert len(result) == 1
        assert result[0]["age"] == 30

    def test_where_eq_operator_explicit(self):
        items = [{"age": 20}, {"age": 30}, {"age": 40}]
        result = where(items, "age", 30, "eq")
        assert len(result) == 1
        assert result[0]["age"] == 30

    def test_where_ne_operator(self):
        items = [{"age": 20}, {"age": 30}, {"age": 40}]
        result = where(items, "age", 30, "ne")
        assert len(result) == 2
        assert result[0]["age"] == 20
        assert result[1]["age"] == 40

    def test_where_gt_operator(self):
        items = [{"age": 20}, {"age": 30}, {"age": 40}]
        result = where(items, "age", 25, "gt")
        assert len(result) == 2
        assert result[0]["age"] == 30
        assert result[1]["age"] == 40

    def test_where_gt_operator_boundary(self):
        items = [{"age": 20}, {"age": 30}, {"age": 40}]
        result = where(items, "age", 30, "gt")
        assert len(result) == 1
        assert result[0]["age"] == 40

    def test_where_gte_operator(self):
        items = [{"age": 20}, {"age": 30}, {"age": 40}]
        result = where(items, "age", 30, "gte")
        assert len(result) == 2
        assert result[0]["age"] == 30
        assert result[1]["age"] == 40

    def test_where_lt_operator(self):
        items = [{"age": 20}, {"age": 30}, {"age": 40}]
        result = where(items, "age", 35, "lt")
        assert len(result) == 2
        assert result[0]["age"] == 20
        assert result[1]["age"] == 30

    def test_where_lt_operator_boundary(self):
        items = [{"age": 20}, {"age": 30}, {"age": 40}]
        result = where(items, "age", 30, "lt")
        assert len(result) == 1
        assert result[0]["age"] == 20

    def test_where_lte_operator(self):
        items = [{"age": 20}, {"age": 30}, {"age": 40}]
        result = where(items, "age", 30, "lte")
        assert len(result) == 2
        assert result[0]["age"] == 20
        assert result[1]["age"] == 30

    def test_where_in_operator_value_in_item_list(self):
        """Test 'in' when item has a list and we check if value is in it."""
        items = [
            {"tags": ["python", "web"]},
            {"tags": ["rust", "systems"]},
            {"tags": ["python", "data"]},
        ]
        result = where(items, "tags", "python", "in")
        assert len(result) == 2
        assert result[0]["tags"] == ["python", "web"]
        assert result[1]["tags"] == ["python", "data"]

    def test_where_in_operator_item_value_in_provided_list(self):
        """Test 'in' when we provide a list and check if item value is in it."""
        items = [
            {"status": "active"},
            {"status": "archived"},
            {"status": "draft"},
        ]
        result = where(items, "status", ["active", "draft"], "in")
        assert len(result) == 2
        assert result[0]["status"] == "active"
        assert result[1]["status"] == "draft"

    def test_where_in_operator_no_match(self):
        items = [{"tags": ["python"]}, {"tags": ["rust"]}]
        result = where(items, "tags", "java", "in")
        assert result == []

    def test_where_not_in_operator(self):
        items = [
            {"status": "active"},
            {"status": "archived"},
            {"status": "draft"},
        ]
        result = where(items, "status", ["archived"], "not_in")
        assert len(result) == 2
        assert result[0]["status"] == "active"
        assert result[1]["status"] == "draft"

    def test_where_not_in_operator_with_item_list(self):
        """Test 'not_in' when item has a list."""
        items = [
            {"tags": ["python", "web"]},
            {"tags": ["rust", "systems"]},
        ]
        result = where(items, "tags", "python", "not_in")
        assert len(result) == 1
        assert result[0]["tags"] == ["rust", "systems"]

    def test_where_unknown_operator_falls_back_to_eq(self):
        items = [{"age": 30}, {"age": 40}]
        result = where(items, "age", 30, "unknown_op")
        assert len(result) == 1
        assert result[0]["age"] == 30

    def test_where_operator_with_incompatible_types(self):
        """Test that incompatible type comparisons are skipped gracefully."""
        items = [{"age": 30}, {"age": "thirty"}, {"age": 40}]
        result = where(items, "age", 25, "gt")
        # String "thirty" should be skipped, not cause an error
        assert len(result) == 2
        assert result[0]["age"] == 30
        assert result[1]["age"] == 40

    def test_where_operator_with_nested_attributes(self):
        """Test operators work with nested attribute access."""
        items = [
            {"metadata": {"priority": 1}},
            {"metadata": {"priority": 5}},
            {"metadata": {"priority": 3}},
        ]
        result = where(items, "metadata.priority", 3, "gte")
        assert len(result) == 2
