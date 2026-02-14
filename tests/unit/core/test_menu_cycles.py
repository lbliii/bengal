import pytest

from bengal.core.menu import MenuBuilder, MenuItem
from bengal.errors import BengalContentError


class TestMenuCircularDependencies:
    def test_menu_parent_child_cycle_raises(self):
        builder = MenuBuilder()
        # Build a cycle via identifiers: p -> c -> p
        builder.add_from_config(
            [
                {"name": "Parent", "url": "/parent", "identifier": "p"},
                {"name": "Child", "url": "/child", "parent": "p", "identifier": "c"},
            ]
        )
        # Inject the cycle by marking parent of "p" as "c" via an additional child that uses
        # the same identifier. Since MenuBuilder uses identifier as key, simulate by building then
        # manually linking children to force a cycle.
        builder.build_hierarchy()
        # Find nodes
        by_id = {item.identifier: item for item in builder.items}
        p = by_id["p"]
        c = by_id["c"]
        # Force a cycle
        if c not in p.children:
            p.children.append(c)
        c.children.append(p)

        # Now the cycle should be detected by the cycle checker when rebuilding
        with pytest.raises(BengalContentError):
            builder.build_hierarchy()

        with pytest.raises(BengalContentError):
            builder.build_hierarchy()

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
        builder.add_from_config([{"name": "Self", "url": "/self", "identifier": "self"}])
        builder.build_hierarchy()

        # Manually create self-reference
        by_id = {item.identifier: item for item in builder.items}
        self_item = by_id["self"]
        self_item.children.append(self_item)

        with pytest.raises(BengalContentError):
            builder.build_hierarchy()

    def test_indirect_cycle_three_nodes(self):
        """Test indirect cycle: A → B → C → A."""
        builder = MenuBuilder()
        builder.add_from_config(
            [
                {"name": "A", "url": "/a", "identifier": "a"},
                {"name": "B", "url": "/b", "parent": "a", "identifier": "b"},
                {"name": "C", "url": "/c", "parent": "b", "identifier": "c"},
            ]
        )
        builder.build_hierarchy()

        # Create cycle: C → A
        by_id = {item.identifier: item for item in builder.items}
        by_id["c"].children.append(by_id["a"])

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
