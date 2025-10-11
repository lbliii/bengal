"""
Tests for the menu system.
"""

from bengal.core.menu import MenuItem, MenuBuilder


class TestMenuItem:
    """Test MenuItem class."""
    
    def test_create_menu_item(self):
        """Test creating a basic menu item."""
        item = MenuItem(name="Home", url="/")
        assert item.name == "Home"
        assert item.url == "/"
        assert item.weight == 0
        assert item.active is False
        assert item.children == []
    
    def test_menu_item_with_parent(self):
        """Test menu item with parent relationship."""
        item = MenuItem(
            name="Getting Started",
            url="/docs/getting-started/",
            parent="docs",
            weight=1
        )
        assert item.parent == "docs"
        assert item.weight == 1
    
    def test_menu_item_identifier_auto_generation(self):
        """Test that identifier is auto-generated from name."""
        item = MenuItem(name="Getting Started", url="/docs/")
        assert item.identifier == "getting-started"
        
        item2 = MenuItem(name="My_Cool Item", url="/")
        assert item2.identifier == "my-cool-item"
    
    def test_menu_item_add_child(self):
        """Test adding children to menu items."""
        parent = MenuItem(name="Docs", url="/docs/", identifier="docs")
        child1 = MenuItem(name="Guide", url="/docs/guide/", weight=2)
        child2 = MenuItem(name="Intro", url="/docs/intro/", weight=1)
        
        parent.add_child(child1)
        parent.add_child(child2)
        
        assert len(parent.children) == 2
        # Children should be sorted by weight
        assert parent.children[0].name == "Intro"
        assert parent.children[1].name == "Guide"
    
    def test_mark_active(self):
        """Test marking menu items as active."""
        item = MenuItem(name="Home", url="/")
        
        # Exact match
        result = item.mark_active("/")
        assert result is True
        assert item.active is True
        
        # Different URL
        item2 = MenuItem(name="About", url="/about/")
        result = item2.mark_active("/")
        assert result is False
        assert item2.active is False
    
    def test_mark_active_with_children(self):
        """Test active trail marking with nested items."""
        parent = MenuItem(name="Docs", url="/docs/", identifier="docs")
        child = MenuItem(name="Guide", url="/docs/guide/")
        parent.add_child(child)
        
        # Mark child as active
        parent.mark_active("/docs/guide/")
        
        assert parent.active_trail is True
        assert child.active is True
    
    def test_to_dict(self):
        """Test converting menu item to dictionary."""
        parent = MenuItem(name="Docs", url="/docs/", identifier="docs")
        child = MenuItem(name="Guide", url="/docs/guide/")
        parent.add_child(child)
        
        data = parent.to_dict()
        assert data['name'] == "Docs"
        assert data['url'] == "/docs/"
        assert data['active'] is False
        assert data['active_trail'] is False
        assert len(data['children']) == 1
        assert data['children'][0]['name'] == "Guide"


class TestMenuBuilder:
    """Test MenuBuilder class."""
    
    def test_add_from_config(self):
        """Test adding menu items from config."""
        builder = MenuBuilder()
        config = [
            {'name': 'Home', 'url': '/', 'weight': 1},
            {'name': 'About', 'url': '/about/', 'weight': 2}
        ]
        
        builder.add_from_config(config)
        menu = builder.build_hierarchy()
        
        assert len(menu) == 2
        assert menu[0].name == "Home"
        assert menu[1].name == "About"
    
    def test_build_hierarchy_with_parents(self):
        """Test building hierarchical menu structure."""
        builder = MenuBuilder()
        config = [
            {'name': 'Docs', 'url': '/docs/', 'identifier': 'docs', 'weight': 1},
            {'name': 'Getting Started', 'url': '/docs/intro/', 'parent': 'docs', 'weight': 1},
            {'name': 'Advanced', 'url': '/docs/advanced/', 'parent': 'docs', 'weight': 2}
        ]
        
        builder.add_from_config(config)
        menu = builder.build_hierarchy()
        
        # Should only have one top-level item
        assert len(menu) == 1
        assert menu[0].name == "Docs"
        
        # Should have two children
        assert len(menu[0].children) == 2
        assert menu[0].children[0].name == "Getting Started"
        assert menu[0].children[1].name == "Advanced"
    
    def test_mark_active_items(self):
        """Test marking active items in a menu."""
        builder = MenuBuilder()
        config = [
            {'name': 'Home', 'url': '/', 'weight': 1},
            {'name': 'About', 'url': '/about/', 'weight': 2}
        ]
        
        builder.add_from_config(config)
        menu = builder.build_hierarchy()
        
        # Mark /about/ as active
        builder.mark_active_items('/about/', menu)
        
        assert menu[0].active is False
        assert menu[1].active is True
    
    def test_add_from_page(self):
        """Test adding menu items from page frontmatter."""
        # Create a mock page
        class MockPage:
            title = "Contact Page"
            url = "/contact/"
        
        builder = MenuBuilder()
        page = MockPage()
        
        # Test with explicit name
        menu_data = {
            'name': 'Contact',
            'weight': 5
        }
        builder.add_from_page(page, 'main', menu_data)
        menu = builder.build_hierarchy()
        
        assert len(menu) == 1
        assert menu[0].name == "Contact"
        assert menu[0].url == "/contact/"
        assert menu[0].weight == 5
    
    def test_add_from_page_uses_title_fallback(self):
        """Test that page title is used if name not provided."""
        class MockPage:
            title = "My Page Title"
            url = "/my-page/"
        
        builder = MenuBuilder()
        page = MockPage()
        menu_data = {'weight': 10}  # No name provided
        
        builder.add_from_page(page, 'main', menu_data)
        menu = builder.build_hierarchy()
        
        assert len(menu) == 1
        assert menu[0].name == "My Page Title"
    
    def test_orphaned_children_go_to_root(self):
        """Test that children with missing parents go to root level."""
        builder = MenuBuilder()
        config = [
            {'name': 'Lost Child', 'url': '/lost/', 'parent': 'nonexistent'}
        ]
        
        builder.add_from_config(config)
        menu = builder.build_hierarchy()
        
        # Should appear at root level since parent doesn't exist
        assert len(menu) == 1
        assert menu[0].name == "Lost Child"

