import pytest

from bengal.core.menu import MenuBuilder, MenuItem
from bengal.errors import BengalContentError


class TestMenuCircularDependencies:
    def test_menu_parent_child_cycle_raises(self):
        builder = MenuBuilder()
        builder.add_from_config(
            [
                {"name": "Parent", "url": "/parent", "parent": "c", "identifier": "p"},
                {"name": "Child", "url": "/child", "parent": "p", "identifier": "c"},
            ]
        )

        with pytest.raises(BengalContentError):
            builder.build_hierarchy()

    def test_rootless_parent_cycle_raises(self):
        builder = MenuBuilder()
        builder.add_from_config(
            [
                {"name": "A", "url": "/a", "parent": "b", "identifier": "a"},
                {"name": "B", "url": "/b", "parent": "a", "identifier": "b"},
            ]
        )

        with pytest.raises(BengalContentError):
            builder.build_hierarchy()

    def test_self_parent_cycle_raises(self):
        builder = MenuBuilder()
        builder.add_from_config(
            [{"name": "Self", "url": "/self", "parent": "self", "identifier": "self"}]
        )

        with pytest.raises(BengalContentError):
            builder.build_hierarchy()

    def test_repeated_build_hierarchy_is_idempotent(self):
        builder = MenuBuilder()
        builder.add_from_config(
            [
                {"name": "Root", "url": "/", "identifier": "root"},
                {"name": "Child", "url": "/child", "parent": "root", "identifier": "child"},
            ]
        )

        first_roots = builder.build_hierarchy()
        second_roots = builder.build_hierarchy()

        assert first_roots == second_roots
        assert len(second_roots) == 1
        assert [child.identifier for child in second_roots[0].children] == ["child"]

    def test_valid_tree_builds(self):
        builder = MenuBuilder()
        builder.add_from_config(
            [
                {"name": "Root", "url": "/", "identifier": "root"},
                {"name": "Child", "url": "/c", "parent": "root", "identifier": "c"},
            ]
        )
        roots = builder.build_hierarchy()
        assert len(roots) == 1
        assert roots[0].name == "Root"


class TestCycleDetectionEdgeCases:
    """Edge case tests for cycle detection algorithm.

    The _has_cycle() method uses backtracking with O(d) space complexity
    instead of O(n × d) from copying the path set on each recursive call.

    """

    def test_self_referencing_item(self):
        """Test that a self-referencing item is detected as a cycle."""
        builder = MenuBuilder()
        builder.add_from_config(
            [{"name": "Self", "url": "/self", "parent": "self", "identifier": "self"}]
        )

        with pytest.raises(BengalContentError):
            builder.build_hierarchy()

    def test_indirect_cycle_three_nodes(self):
        """Test indirect cycle: A → B → C → A."""
        builder = MenuBuilder()
        builder.add_from_config(
            [
                {"name": "A", "url": "/a", "parent": "c", "identifier": "a"},
                {"name": "B", "url": "/b", "parent": "a", "identifier": "b"},
                {"name": "C", "url": "/c", "parent": "b", "identifier": "c"},
            ]
        )

        with pytest.raises(BengalContentError):
            builder.build_hierarchy()

    def test_deeply_nested_no_cycle(self):
        """Test deeply nested menu (10+ levels) without cycle."""
        builder = MenuBuilder()
        config = [{"name": "Level 0", "url": "/l0", "identifier": "l0"}] + [
            {
                "name": f"Level {i}",
                "url": f"/l{i}",
                "parent": f"l{i - 1}",
                "identifier": f"l{i}",
            }
            for i in range(1, 15)
        ]

        builder.add_from_config(config)
        roots = builder.build_hierarchy()

        # Should build successfully
        assert len(roots) == 1
        assert roots[0].name == "Level 0"

        # Verify depth
        current = roots[0]
        depth = 0
        while current.children:
            depth += 1
            current = current.children[0]
        assert depth == 14

    def test_wide_tree_no_cycle(self):
        """Test wide tree (many children at each level) without cycle."""
        builder = MenuBuilder()
        config = [{"name": "Root", "url": "/root", "identifier": "root"}] + [
            {
                "name": f"Child {i}",
                "url": f"/child{i}",
                "parent": "root",
                "identifier": f"child{i}",
                "weight": i,
            }
            for i in range(50)
        ]

        builder.add_from_config(config)
        roots = builder.build_hierarchy()

        assert len(roots) == 1
        assert len(roots[0].children) == 50
        # Children should be sorted by weight
        assert roots[0].children[0].name == "Child 0"
        assert roots[0].children[49].name == "Child 49"

    def test_menu_with_none_identifier(self):
        """Test that items with None identifier don't cause issues."""
        # MenuItem auto-generates identifier from name, but test edge case
        item = MenuItem(name="Test", url="/test")
        item.identifier = None  # Force None

        builder = MenuBuilder()
        builder.items = [item]

        # Should not raise (None identifiers are skipped in cycle detection)
        roots = builder.build_hierarchy()
        assert len(roots) == 1

    def test_backtracking_does_not_pollute_path(self):
        """Test that backtracking correctly removes items from path.

        This verifies the backtracking optimization doesn't leave stale
        entries in the path set, which would cause false positives.
        """
        builder = MenuBuilder()
        # Create a tree where backtracking is essential:
        # Root → A → A1
        #      → B → B1
        # If backtracking fails, visiting A1 then B would incorrectly
        # think B is in the path.
        builder.add_from_config(
            [
                {"name": "Root", "url": "/", "identifier": "root"},
                {"name": "A", "url": "/a", "parent": "root", "identifier": "a"},
                {"name": "A1", "url": "/a1", "parent": "a", "identifier": "a1"},
                {"name": "B", "url": "/b", "parent": "root", "identifier": "b"},
                {"name": "B1", "url": "/b1", "parent": "b", "identifier": "b1"},
            ]
        )

        # Should build without false cycle detection
        roots = builder.build_hierarchy()
        assert len(roots) == 1
        assert len(roots[0].children) == 2  # A and B
