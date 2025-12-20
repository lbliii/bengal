"""
Tests for navigation dataclasses.

Tests cover:
- BreadcrumbItem
- PaginationItem and PaginationInfo
- NavTreeItem
- TocGroupItem
- AutoNavItem
- Dict-style access for Jinja template compatibility
"""

from __future__ import annotations

import pytest

from bengal.rendering.template_functions.navigation_models import (
    AutoNavItem,
    BreadcrumbItem,
    NavTreeItem,
    PaginationInfo,
    PaginationItem,
    TocGroupItem,
)


class TestBreadcrumbItem:
    """Tests for BreadcrumbItem dataclass."""

    def test_create_with_required_fields(self):
        """Test creating BreadcrumbItem with required fields."""
        item = BreadcrumbItem(title="Home", url="/")

        assert item.title == "Home"
        assert item.url == "/"
        assert item.is_current is False

    def test_create_with_is_current_true(self):
        """Test creating BreadcrumbItem as current page."""
        item = BreadcrumbItem(title="About", url="/about/", is_current=True)

        assert item.is_current is True

    def test_dict_style_access(self):
        """Test dict-style access for template compatibility."""
        item = BreadcrumbItem(title="Home", url="/")

        assert item["title"] == "Home"
        assert item["url"] == "/"
        assert item["is_current"] is False

    def test_keys_method(self):
        """Test keys() returns field names."""
        item = BreadcrumbItem(title="Home", url="/")

        keys = item.keys()
        assert "title" in keys
        assert "url" in keys
        assert "is_current" in keys

    def test_get_method(self):
        """Test get() with default value."""
        item = BreadcrumbItem(title="Home", url="/")

        assert item.get("title") == "Home"
        assert item.get("nonexistent", "default") == "default"

    def test_uses_slots(self):
        """Test BreadcrumbItem uses __slots__ for memory efficiency."""
        assert hasattr(BreadcrumbItem, "__slots__")


class TestPaginationItem:
    """Tests for PaginationItem dataclass."""

    def test_create_regular_page(self):
        """Test creating regular pagination item."""
        item = PaginationItem(num=1, url="/blog/")

        assert item.num == 1
        assert item.url == "/blog/"
        assert item.is_current is False
        assert item.is_ellipsis is False

    def test_create_current_page(self):
        """Test creating current page item."""
        item = PaginationItem(num=3, url="/blog/page/3/", is_current=True)

        assert item.is_current is True

    def test_create_ellipsis(self):
        """Test creating ellipsis item."""
        item = PaginationItem(num=None, url=None, is_ellipsis=True)

        assert item.num is None
        assert item.url is None
        assert item.is_ellipsis is True

    def test_dict_style_access(self):
        """Test dict-style access for template compatibility."""
        item = PaginationItem(num=2, url="/blog/page/2/")

        assert item["num"] == 2
        assert item["url"] == "/blog/page/2/"

    def test_keys_method(self):
        """Test keys() returns field names."""
        item = PaginationItem(num=1, url="/")

        keys = item.keys()
        assert "num" in keys
        assert "url" in keys
        assert "is_current" in keys
        assert "is_ellipsis" in keys


class TestPaginationInfo:
    """Tests for PaginationInfo dataclass."""

    def test_create_with_pages(self):
        """Test creating PaginationInfo with pages."""
        pages = [
            PaginationItem(num=1, url="/blog/", is_current=True),
            PaginationItem(num=2, url="/blog/page/2/"),
        ]
        info = PaginationInfo(
            pages=pages,
            first={"num": 1, "url": "/blog/"},
            last={"num": 2, "url": "/blog/page/2/"},
        )

        assert len(info.pages) == 2
        assert info.prev is None
        assert info.next is None

    def test_create_with_prev_next(self):
        """Test creating PaginationInfo with prev/next."""
        pages = [PaginationItem(num=2, url="/blog/page/2/", is_current=True)]
        info = PaginationInfo(
            pages=pages,
            prev={"num": 1, "url": "/blog/"},
            next={"num": 3, "url": "/blog/page/3/"},
            first={"num": 1, "url": "/blog/"},
            last={"num": 5, "url": "/blog/page/5/"},
        )

        assert info.prev == {"num": 1, "url": "/blog/"}
        assert info.next == {"num": 3, "url": "/blog/page/3/"}

    def test_dict_style_access(self):
        """Test dict-style access for template compatibility."""
        pages = [PaginationItem(num=1, url="/")]
        info = PaginationInfo(pages=pages)

        assert info["pages"] == pages


class TestNavTreeItem:
    """Tests for NavTreeItem dataclass."""

    def test_create_simple_item(self):
        """Test creating simple nav tree item."""
        item = NavTreeItem(title="Home", url="/")

        assert item.title == "Home"
        assert item.url == "/"
        assert item.is_current is False
        assert item.is_in_active_trail is False
        assert item.is_section is False
        assert item.depth == 0
        assert item.children == []
        assert item.has_children is False

    def test_create_current_item(self):
        """Test creating current nav tree item."""
        item = NavTreeItem(title="About", url="/about/", is_current=True)

        assert item.is_current is True

    def test_create_section_item(self):
        """Test creating section nav tree item."""
        item = NavTreeItem(title="Docs", url="/docs/", is_section=True, has_children=True)

        assert item.is_section is True
        assert item.has_children is True

    def test_create_with_children(self):
        """Test creating nav tree item with children."""
        child1 = NavTreeItem(title="Child 1", url="/parent/child1/", depth=1)
        child2 = NavTreeItem(title="Child 2", url="/parent/child2/", depth=1)
        parent = NavTreeItem(
            title="Parent",
            url="/parent/",
            is_section=True,
            children=[child1, child2],
            has_children=True,
        )

        assert len(parent.children) == 2
        assert parent.children[0].title == "Child 1"

    def test_create_in_active_trail(self):
        """Test creating item in active trail."""
        item = NavTreeItem(title="Docs", url="/docs/", is_in_active_trail=True)

        assert item.is_in_active_trail is True

    def test_dict_style_access(self):
        """Test dict-style access for template compatibility."""
        item = NavTreeItem(title="Home", url="/", depth=0)

        assert item["title"] == "Home"
        assert item["depth"] == 0
        assert item["children"] == []

    def test_keys_method(self):
        """Test keys() returns all field names."""
        item = NavTreeItem(title="Home", url="/")

        keys = item.keys()
        assert "title" in keys
        assert "url" in keys
        assert "is_current" in keys
        assert "is_in_active_trail" in keys
        assert "is_section" in keys
        assert "depth" in keys
        assert "children" in keys
        assert "has_children" in keys


class TestTocGroupItem:
    """Tests for TocGroupItem dataclass."""

    def test_create_simple_group(self):
        """Test creating simple TOC group."""
        header = {"id": "section-1", "title": "Section 1", "level": 1}
        group = TocGroupItem(header=header)

        assert group.header == header
        assert group.children == []
        assert group.is_group is False

    def test_create_group_with_children(self):
        """Test creating TOC group with children."""
        header = {"id": "section-1", "title": "Section 1", "level": 1}
        children = [
            {"id": "subsection-1", "title": "Subsection 1", "level": 2},
            {"id": "subsection-2", "title": "Subsection 2", "level": 2},
        ]
        group = TocGroupItem(header=header, children=children, is_group=True)

        assert len(group.children) == 2
        assert group.is_group is True

    def test_dict_style_access(self):
        """Test dict-style access for template compatibility."""
        header = {"id": "section-1", "title": "Section 1", "level": 1}
        group = TocGroupItem(header=header)

        assert group["header"] == header
        assert group["is_group"] is False


class TestAutoNavItem:
    """Tests for AutoNavItem dataclass."""

    def test_create_simple_item(self):
        """Test creating simple auto nav item."""
        item = AutoNavItem(name="Home", url="/")

        assert item.name == "Home"
        assert item.url == "/"
        assert item.weight == 0
        assert item.identifier == ""
        assert item.parent is None
        assert item.icon is None

    def test_create_with_weight(self):
        """Test creating auto nav item with weight."""
        item = AutoNavItem(name="About", url="/about/", weight=10)

        assert item.weight == 10

    def test_create_with_identifier(self):
        """Test creating auto nav item with identifier."""
        item = AutoNavItem(name="Docs", url="/docs/", identifier="docs")

        assert item.identifier == "docs"

    def test_create_nested_item(self):
        """Test creating nested auto nav item with parent."""
        item = AutoNavItem(
            name="Getting Started",
            url="/docs/getting-started/",
            identifier="getting-started",
            parent="docs",
        )

        assert item.parent == "docs"

    def test_create_with_icon(self):
        """Test creating auto nav item with icon."""
        item = AutoNavItem(name="Settings", url="/settings/", icon="cog")

        assert item.icon == "cog"

    def test_dict_style_access(self):
        """Test dict-style access for template compatibility."""
        item = AutoNavItem(name="Home", url="/", weight=5)

        assert item["name"] == "Home"
        assert item["weight"] == 5

    def test_keys_method(self):
        """Test keys() returns all field names."""
        item = AutoNavItem(name="Home", url="/")

        keys = item.keys()
        assert "name" in keys
        assert "url" in keys
        assert "weight" in keys
        assert "identifier" in keys
        assert "parent" in keys
        assert "icon" in keys


class TestDataclassSlots:
    """Tests that all navigation models use __slots__ for memory efficiency."""

    @pytest.mark.parametrize(
        "model_class",
        [
            BreadcrumbItem,
            PaginationItem,
            PaginationInfo,
            NavTreeItem,
            TocGroupItem,
            AutoNavItem,
        ],
    )
    def test_uses_slots(self, model_class):
        """Test model uses __slots__."""
        assert hasattr(model_class, "__slots__")


class TestTemplateCompatibility:
    """Tests for Jinja template compatibility patterns."""

    def test_breadcrumb_iteration(self):
        """Test iterating over breadcrumb keys like in Jinja template."""
        item = BreadcrumbItem(title="Home", url="/", is_current=False)

        # Simulate: {% for key in item.keys() %}{{ item[key] }}{% endfor %}
        # Using keys() explicitly to match Jinja template pattern
        keys = item.keys()
        values = [item[key] for key in keys]
        assert "Home" in values
        assert "/" in values

    def test_nav_tree_recursive_access(self):
        """Test recursive nav tree access like in Jinja macro."""
        child = NavTreeItem(title="Child", url="/child/", depth=1)
        parent = NavTreeItem(
            title="Parent",
            url="/parent/",
            children=[child],
            has_children=True,
        )

        # Simulate: {% if item.has_children %}{% for child in item.children %}...
        if parent["has_children"]:
            for child_item in parent["children"]:
                assert child_item["title"] == "Child"

    def test_pagination_conditional_access(self):
        """Test pagination conditional access like in Jinja template."""
        pages = [
            PaginationItem(num=1, url="/", is_current=False),
            PaginationItem(num=None, url=None, is_ellipsis=True),
            PaginationItem(num=5, url="/page/5/", is_current=True),
        ]

        # Simulate: {% if item.is_ellipsis %}...{% elif item.is_current %}...
        for item in pages:
            if item["is_ellipsis"]:
                assert item["num"] is None
            elif item["is_current"]:
                assert item["num"] == 5
