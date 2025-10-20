import pytest

from bengal.core.menu import MenuBuilder


class TestMenuCircularDependencies:
    def test_menu_parent_child_cycle_raises(self):
        builder = MenuBuilder()
        builder.add_from_config(
            [
                {"name": "Parent", "url": "/parent", "identifier": "p"},
                {"name": "Child", "url": "/child", "parent": "p", "identifier": "c"},
                # Cycle: Parent is a child of Child
                {"name": "ParentDup", "url": "/parent", "parent": "c", "identifier": "p"},
            ]
        )

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
