import pytest

from bengal.core.menu import MenuBuilder


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
        p.children.append(c) if c not in p.children else None
        c.children.append(p)

        # Now the cycle should be detected by the cycle checker when rebuilding
        with pytest.raises(ValueError):
            builder.build_hierarchy()

        with pytest.raises(ValueError):
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
